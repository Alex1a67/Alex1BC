package com.alex1bc.controller

import android.app.Application
import android.content.Context
import android.view.WindowManager
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.alex1bc.controller.net.Connection
import com.alex1bc.controller.net.LinkState
import com.alex1bc.controller.net.Protocol
import com.alex1bc.controller.net.QrPayload
import com.alex1bc.controller.sensor.MotionSensor
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

/** Control values written by the touch UI and read by the 60 Hz send loop (never queued: latest wins). */
class Axes {
    @Volatile var mx = 0f; @Volatile var my = 0f; @Volatile var mz = 0f
    @Volatile var lx = 0f; @Volatile var ly = 0f; @Volatile var zoom = 0f
    fun idle() = mx == 0f && my == 0f && mz == 0f && lx == 0f && ly == 0f && zoom == 0f
}

class AppViewModel(app: Application) : AndroidViewModel(app) {
    val prefs = Prefs(app)
    val conn = Connection(prefs, viewModelScope)
    val motion = MotionSensor(app)
    val axes = Axes()

    private val _mode = MutableStateFlow(prefs.mode)
    val mode: StateFlow<String> = _mode
    private val _frozen = MutableStateFlow(false)
    val frozen: StateFlow<Boolean> = _frozen

    init {
        viewModelScope.launch {                                   // sensors only run while connected (battery)
            conn.link.collect { if (it is LinkState.Connected) motion.start() else motion.stop() }
        }
        viewModelScope.launch {
            var lastSend = 0L
            while (true) {
                delay(16)
                if (conn.link.value !is LinkState.Connected || conn.backlog() > 4096) continue
                val m = _mode.value
                val q = if (m != "analog") motion.latest() else null
                val now = System.currentTimeMillis()
                if (m == "analog" && axes.idle() && now - lastSend < 200) continue
                conn.send(Protocol.inputJson(m, axes.mx, axes.my, axes.mz, axes.lx, axes.ly, axes.zoom, q, screenAngle(), _frozen.value))
                lastSend = now
            }
        }
    }

    @Suppress("DEPRECATION")
    private fun screenAngle(): Int {
        val wm = getApplication<Application>().getSystemService(Context.WINDOW_SERVICE) as WindowManager
        return wm.defaultDisplay.rotation * 90          // Surface.ROTATION_90 == device turned 90 deg counter-clockwise, same as W3C
    }

    val hasSensor: Boolean get() = motion.available
    fun setMode(m: String) { _mode.value = m; prefs.mode = m }
    fun toggleFreeze() { _frozen.value = !_frozen.value; if (!_frozen.value) conn.cmd("recenter") }
    fun connectQr(p: QrPayload) = conn.connect(p)
    fun finishOnboarding() { prefs.onboarded = true }
    override fun onCleared() { motion.stop(); conn.disconnect() }
}
