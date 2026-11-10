package com.alex1bc.controller.net

import java.util.Locale

/** What the Blender QR code contains: https://<ip>:<port>/#t=<9 digits>&fp=<SHA-256 of the TLS cert> */
data class QrPayload(val scheme: String, val host: String, val port: Int, val code: String, val fingerprint: String?) {
    val secure: Boolean get() = scheme == "https"
    val wsUrl: String get() = (if (secure) "wss" else "ws") + "://" + host + ":" + port + "/ws"
}

object Protocol {
    private val qrRegex = Regex("^(https?)://([^/:#\\s]+):(\\d{2,5})/?#(.+)$")
    private val fpRegex = Regex("[0-9A-F]{64}")

    /** Returns null when the text is not an Alex1BC QR. */
    fun parseQr(text: String): QrPayload? {
        val m = qrRegex.matchEntire(text.trim()) ?: return null
        val params = HashMap<String, String>()
        for (part in m.groupValues[4].split('&')) {
            val i = part.indexOf('=')
            if (i > 0) params[part.substring(0, i)] = part.substring(i + 1)
        }
        val code = params["t"]?.filter { it.isDigit() } ?: return null
        if (code.length != 9) return null
        val port = m.groupValues[3].toInt()
        if (port !in 1..65535) return null
        val fp = params["fp"]?.uppercase(Locale.ROOT)?.takeIf { fpRegex.matches(it) }
        val scheme = m.groupValues[1]
        if (scheme == "https" && fp == null) return null          // never connect over TLS without a pinned fingerprint
        return QrPayload(scheme, m.groupValues[2], port, code, fp)
    }

    /** Manual entry is limited to the USB route (loopback), which needs no certificate. */
    fun parseManual(hostPort: String, code: String): QrPayload? {
        val digits = code.filter { it.isDigit() }
        if (digits.length != 9) return null
        val hp = hostPort.trim().removePrefix("http://")
        val i = hp.lastIndexOf(':')
        if (i <= 0) return null
        val host = hp.substring(0, i)
        val port = hp.substring(i + 1).toIntOrNull() ?: return null
        if (host != "localhost" && host != "127.0.0.1") return null
        if (port !in 1..65535) return null
        return QrPayload("http", host, port, digits, null)
    }

    fun esc(s: String): String {
        val sb = StringBuilder()
        for (c in s) when {
            c == '"' -> sb.append("\\\"")
            c == '\\' -> sb.append("\\\\")
            c < ' ' -> sb.append(' ')
            else -> sb.append(c)
        }
        return sb.toString()
    }

    private fun f(v: Float): String = String.format(Locale.US, "%.4f", if (v.isNaN() || v.isInfinite()) 0f else v)

    fun pairJson(code: String, name: String) = """{"t":"pair","code":"${esc(code)}","name":"${esc(name)}"}"""
    fun resumeJson(session: String) = """{"t":"resume","session":"${esc(session)}"}"""
    fun pingJson(ts: Long, rtt: Int) = """{"t":"ping","ts":$ts,"rtt":$rtt}"""
    fun cmdJson(c: String, v: Float? = null) = if (v == null) """{"t":"cmd","c":"${esc(c)}"}""" else """{"t":"cmd","c":"${esc(c)}","v":${f(v)}}"""
    fun cmdJson(c: String, v: String) = """{"t":"cmd","c":"${esc(c)}","v":"${esc(v)}"}"""

    /** q = device->world quaternion [w,x,y,z] from the rotation-vector sensor, screenDeg = display rotation (0/90/180/270). */
    fun inputJson(mode: String, mx: Float, my: Float, mz: Float, lx: Float, ly: Float, zoom: Float,
                  q: FloatArray?, screenDeg: Int, frozen: Boolean): String {
        val sb = StringBuilder(160)
        sb.append("{\"t\":\"in\",\"mode\":\"").append(esc(mode)).append("\",\"mx\":").append(f(mx)).append(",\"my\":").append(f(my))
            .append(",\"mz\":").append(f(mz)).append(",\"lx\":").append(f(lx)).append(",\"ly\":").append(f(ly))
            .append(",\"zoom\":").append(f(zoom)).append(",\"fr\":").append(if (frozen) 1 else 0)
        if (q != null && q.size == 4) {
            sb.append(",\"q\":[").append(f(q[0])).append(',').append(f(q[1])).append(',').append(f(q[2])).append(',').append(f(q[3]))
                .append("],\"s\":").append(screenDeg)
        }
        return sb.append('}').toString()
    }
}
