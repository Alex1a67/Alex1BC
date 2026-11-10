package com.alex1bc.controller

import com.alex1bc.controller.net.Protocol
import org.junit.Assert.*
import org.junit.Test

class ProtocolTest {
    private val fp = "AB".repeat(32)
    @Test fun parsesLanQr() {
        val p = Protocol.parseQr("https://192.168.1.20:47800/#t=482913076&fp=$fp")!!
        assertEquals("wss://192.168.1.20:47800/ws", p.wsUrl); assertEquals("482913076", p.code); assertEquals(fp, p.fingerprint)
    }
    @Test fun refusesTlsWithoutFingerprint() = assertNull(Protocol.parseQr("https://10.0.0.2:47800/#t=482913076"))
    @Test fun refusesGarbage() { assertNull(Protocol.parseQr("hello")); assertNull(Protocol.parseQr("https://x:1/#t=12")) }
    @Test fun manualOnlyLoopback() {
        assertNotNull(Protocol.parseManual("localhost:47801", "482 913 076")); assertNull(Protocol.parseManual("192.168.1.5:47801", "482913076"))
    }
    @Test fun inputJsonShape() {
        val j = Protocol.inputJson("hybrid", 0f, 1f, 0f, 0f, 0f, 0f, floatArrayOf(1f, 0f, 0f, 0f), 90, false)
        assertTrue(j.contains("\"q\":[1.0000,0.0000,0.0000,0.0000],\"s\":90")); assertTrue(j.startsWith("{\"t\":\"in\""))
    }
}
