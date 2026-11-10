package com.alex1bc.controller.net

import android.os.Build
import com.alex1bc.controller.Prefs
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import org.json.JSONObject
import java.security.MessageDigest
import java.security.SecureRandom
import java.security.cert.CertificateException
import java.security.cert.X509Certificate
import javax.net.ssl.SSLContext
import javax.net.ssl.TrustManager
import javax.net.ssl.X509TrustManager

sealed interface LinkState {
    data object Idle : LinkState
    data object Connecting : LinkState
    data object Connected : LinkState
    data object Reconnecting : LinkState
    data class Failed(val message: String) : LinkState
}

data class ServerState(
    val cam: String? = null, val cams: List<String> = emptyList(), val lens: Float = 50f, val frame: Int = 1,
    val playing: Boolean = false, val rec: String = "off", val recSeconds: Float = 0f, val takes: Int = 0,
    val blender: String = "",
)

data class Toast(val message: String, val level: String)

/** WebSocket link to the Blender add-on. TLS is pinned to the certificate fingerprint from the QR code. */
class Connection(private val prefs: Prefs, private val scope: CoroutineScope) {
    private val _link = MutableStateFlow<LinkState>(LinkState.Idle)
    val link: StateFlow<LinkState> = _link
    private val _state = MutableStateFlow(ServerState())
    val state: StateFlow<ServerState> = _state
    private val _rtt = MutableStateFlow(0)
    val rtt: StateFlow<Int> = _rtt
    private val _toasts = MutableSharedFlow<Toast>(extraBufferCapacity = 16)
    val toasts: SharedFlow<Toast> = _toasts

    private var ws: WebSocket? = null
    private var target: QrPayload? = null
    private var pendingCode: String? = null
    private var wanted = false
    private var attempts = 0
    private var pingJob: Job? = null
    private var retryJob: Job? = null

    private val deviceName: String get() = (Build.MODEL ?: "Android").take(30)

    fun connect(p: QrPayload) {
        close(keepSession = false)
        target = p; pendingCode = p.code; wanted = true; attempts = 0
        _link.value = LinkState.Connecting
        open()
    }

    /** Reconnect to the last Blender using the saved session token. */
    fun resumeLast(): Boolean {
        val t = prefs.lastTarget() ?: return false
        if (prefs.session == null) return false
        close(keepSession = true)
        target = t; pendingCode = null; wanted = true; attempts = 0
        _link.value = LinkState.Connecting
        open()
        return true
    }

    fun disconnect(forget: Boolean = false) {
        close(keepSession = !forget)
        if (forget) prefs.forget()
        _link.value = LinkState.Idle
    }

    private fun close(keepSession: Boolean) {
        wanted = false; retryJob?.cancel(); pingJob?.cancel()
        ws?.close(1000, "bye"); ws = null
        if (!keepSession) pendingCode = null
        _state.value = ServerState()
    }

    fun send(json: String) { ws?.send(json) }
    fun backlog(): Long = ws?.queueSize() ?: 0L
    fun cmd(c: String) = send(Protocol.cmdJson(c))
    fun cmd(c: String, v: Float) = send(Protocol.cmdJson(c, v))
    fun cmd(c: String, v: String) = send(Protocol.cmdJson(c, v))

    private fun client(p: QrPayload): OkHttpClient {
        val b = OkHttpClient.Builder().readTimeout(java.time.Duration.ZERO)
        val fp = p.fingerprint
        if (p.secure && fp != null) {
            val tm = object : X509TrustManager {
                override fun checkClientTrusted(chain: Array<X509Certificate>, authType: String) {}
                override fun checkServerTrusted(chain: Array<X509Certificate>, authType: String) {
                    val digest = MessageDigest.getInstance("SHA-256").digest(chain[0].encoded)
                    val hex = digest.joinToString("") { "%02X".format(it) }
                    if (hex != fp) throw CertificateException("Certificate does not match the QR code")
                }
                override fun getAcceptedIssuers(): Array<X509Certificate> = emptyArray()
            }
            val ctx = SSLContext.getInstance("TLS")
            ctx.init(null, arrayOf<TrustManager>(tm), SecureRandom())
            b.sslSocketFactory(ctx.socketFactory, tm).hostnameVerifier { _, _ -> true }   // identity = pinned fingerprint
        }
        return b.build()
    }

    private fun open() {
        val p = target ?: return
        val socket = client(p).newWebSocket(Request.Builder().url(p.wsUrl).build(), object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                val code = pendingCode
                val session = prefs.session
                when {
                    code != null -> webSocket.send(Protocol.pairJson(code, deviceName))
                    session != null -> webSocket.send(Protocol.resumeJson(session))
                    else -> { webSocket.close(1000, "no credentials"); _link.value = LinkState.Failed("Scan the QR code again") }
                }
            }
            override fun onMessage(webSocket: WebSocket, text: String) { handle(webSocket, text) }
            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) { lost(webSocket, null) }
            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) { lost(webSocket, t) }
        })
        ws = socket
    }

    private fun handle(socket: WebSocket, text: String) {
        val o = try { JSONObject(text) } catch (e: Exception) { return }
        when (o.optString("t")) {
            "paired" -> {
                prefs.session = o.optString("session"); target?.let { prefs.saveTarget(it) }
                pendingCode = null; attempts = 0
                _link.value = LinkState.Connected
                startPing(socket)
            }
            "state" -> _state.value = ServerState(
                cam = if (o.isNull("cam")) null else o.optString("cam"),
                cams = o.optJSONArray("cams")?.let { a -> List(a.length()) { a.optString(it) } } ?: emptyList(),
                lens = o.optDouble("lens", 50.0).toFloat(), frame = o.optInt("frame", 1), playing = o.optBoolean("playing"),
                rec = o.optString("rec", "off"), recSeconds = o.optDouble("rec_s", 0.0).toFloat(),
                takes = o.optInt("takes"), blender = o.optString("blender"))
            "toast" -> _toasts.tryEmit(Toast(o.optString("msg"), o.optString("level", "info")))
            "pong" -> _rtt.value = (System.nanoTime() / 1_000_000 - o.optLong("ts")).toInt().coerceIn(0, 9999)
            "error" -> {
                if (o.optString("code") == "bad_session") prefs.session = null
                wanted = false
                _link.value = LinkState.Failed(o.optString("msg", "Connection refused"))
                socket.close(1000, "error")
            }
        }
    }

    private fun startPing(socket: WebSocket) {
        pingJob?.cancel()
        pingJob = scope.launch {
            while (true) { socket.send(Protocol.pingJson(System.nanoTime() / 1_000_000, _rtt.value)); delay(1000) }
        }
    }

    private fun lost(socket: WebSocket, t: Throwable?) {
        if (socket !== ws) return
        pingJob?.cancel()
        if (!wanted) return
        attempts++
        if (attempts >= 6 && _link.value !is LinkState.Connected) {
            wanted = false
            _link.value = LinkState.Failed(
                "Can't reach Blender. Same Wi-Fi (not guest)? Alex1BC started in Blender? Firewall allows Blender on private networks? " +
                    (t?.message?.let { "($it)" } ?: ""))
            return
        }
        _link.value = LinkState.Reconnecting
        retryJob?.cancel()
        retryJob = scope.launch { delay(minOf(2500L, 400L * attempts)); if (wanted) open() }
    }
}
