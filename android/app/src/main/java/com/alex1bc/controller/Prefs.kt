package com.alex1bc.controller

import android.content.Context
import com.alex1bc.controller.net.QrPayload

/** Small persistent store: last Blender, session token, chosen mode, onboarding flag. */
class Prefs(context: Context) {
    private val sp = context.getSharedPreferences("alex1bc", Context.MODE_PRIVATE)

    var onboarded: Boolean
        get() = sp.getBoolean("onboarded", false)
        set(v) = sp.edit().putBoolean("onboarded", v).apply()
    var mode: String
        get() = sp.getString("mode", "hybrid") ?: "hybrid"
        set(v) = sp.edit().putString("mode", v).apply()
    var session: String?
        get() = sp.getString("session", null)
        set(v) = sp.edit().putString("session", v).apply()

    fun saveTarget(p: QrPayload) {
        sp.edit().putString("scheme", p.scheme).putString("host", p.host).putInt("port", p.port)
            .putString("fp", p.fingerprint).apply()
    }

    /** The last Blender we paired with (code is not stored, the session token is used instead). */
    fun lastTarget(): QrPayload? {
        val host = sp.getString("host", null) ?: return null
        val scheme = sp.getString("scheme", "https") ?: "https"
        return QrPayload(scheme, host, sp.getInt("port", 47800), "", sp.getString("fp", null))
    }

    fun forget() { sp.edit().remove("session").remove("host").remove("fp").apply() }
}
