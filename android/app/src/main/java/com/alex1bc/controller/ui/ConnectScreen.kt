package com.alex1bc.controller.ui

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.*
import androidx.compose.animation.fadeIn
import androidx.compose.animation.slideInVertically
import androidx.compose.foundation.*
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.alex1bc.controller.AppViewModel
import com.alex1bc.controller.net.LinkState
import com.alex1bc.controller.net.Protocol
import kotlinx.coroutines.delay

/** Cards fade and shrink slightly as they scroll off the top/bottom edge. */
private fun Modifier.edgeFade(state: LazyListState, index: Int) = graphicsLayer {
    val info = state.layoutInfo
    val item = info.visibleItemsInfo.firstOrNull { it.index == index }
    if (item != null) {
        val top = item.offset.toFloat()
        val bottom = info.viewportEndOffset - (item.offset + item.size).toFloat()
        val f = (minOf(top, bottom) / 140f).coerceIn(0f, 1f)
        alpha = 0.3f + 0.7f * f
        val s = 0.93f + 0.07f * f
        scaleX = s; scaleY = s
    }
}

@Composable
private fun Reveal(index: Int, content: @Composable () -> Unit) {
    var shown by remember { mutableStateOf(false) }
    LaunchedEffect(Unit) { delay(120L + index * 110L); shown = true }
    AnimatedVisibility(shown, enter = fadeIn(tween(500)) + slideInVertically(tween(550, easing = FastOutSlowInEasing)) { it / 3 }) { content() }
}

@Composable
private fun Card(modifier: Modifier = Modifier, content: @Composable ColumnScope.() -> Unit) {
    val shape = RoundedCornerShape(22.dp)
    Column(modifier.fillMaxWidth().clip(shape).background(A.Surf).border(1.dp, A.Line, shape).padding(20.dp), content = content)
}

@Composable
private fun Field(value: String, placeholder: String, numeric: Boolean, onChange: (String) -> Unit) {
    BasicTextField(
        value, onChange, singleLine = true,
        textStyle = TextStyle(color = A.Text, fontSize = 20.sp, letterSpacing = 2.sp),
        cursorBrush = SolidColor(A.Bright),
        keyboardOptions = KeyboardOptions(keyboardType = if (numeric) KeyboardType.Number else KeyboardType.Uri),
        modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(14.dp)).background(A.Bg2).padding(16.dp),
        decorationBox = { inner -> Box { if (value.isEmpty()) T(placeholder, 18, A.Text2); inner() } },
    )
}

@Composable
fun ConnectScreen(vm: AppViewModel, onScan: () -> Unit) {
    val link by vm.conn.link.collectAsStateWithLifecycle()
    val listState = rememberLazyListState()
    var host by rememberSaveable { mutableStateOf("localhost:47801") }
    var code by rememberSaveable { mutableStateOf("") }
    var manualError by remember { mutableStateOf<String?>(null) }
    val canResume = remember { vm.prefs.lastTarget() != null && vm.prefs.session != null }
    val inf = rememberInfiniteTransition(label = "c")
    val rot by inf.animateFloat(0f, 360f, infiniteRepeatable(tween(9000, easing = LinearEasing)), label = "r")

    LazyColumn(
        state = listState,
        modifier = Modifier.fillMaxSize().background(A.Bg).windowInsetsPadding(WindowInsets.safeDrawing),
        contentPadding = PaddingValues(horizontal = 22.dp, vertical = 18.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        item {
            Row(
                Modifier.fillMaxWidth().graphicsLayer {
                    val off = if (listState.firstVisibleItemIndex == 0) listState.firstVisibleItemScrollOffset.toFloat() else 900f
                    alpha = (1f - off / 380f).coerceIn(0f, 1f); translationY = off * 0.45f
                    val s = (1f - off / 1600f).coerceIn(0.7f, 1f); scaleX = s; scaleY = s
                },
                verticalAlignment = Alignment.CenterVertically,
            ) {
                LensMark(Modifier.size(72.dp), rotation = rot * 0.5f)
                HGap(16)
                Column {
                    T("Connect to Blender", 26, A.Text, FontWeight.Bold)
                    VGap(4)
                    T("Open Alex1BC in Blender (N panel), then scan.", 14, A.Text2)
                }
            }
        }
        item {
            when (val l = link) {
                is LinkState.Connecting, is LinkState.Reconnecting -> Card {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        CircularProgressIndicator(color = A.Bright, strokeWidth = 3.dp, modifier = Modifier.size(24.dp))
                        HGap(14)
                        T(if (l is LinkState.Reconnecting) "Reconnecting..." else "Connecting to Blender...", 16)
                    }
                }
                is LinkState.Failed -> Card(Modifier.border(1.dp, A.Rec, RoundedCornerShape(22.dp))) { T(l.message, 14, A.Text) }
                else -> {}
            }
        }
        item {
            Reveal(0) {
                Card(Modifier.edgeFade(listState, 2)) {
                    T("WI-FI", 11, A.Bright, FontWeight.Bold, 3f)
                    VGap(8)
                    T("Scan the QR code in Blender", 20, A.Text, FontWeight.Bold)
                    VGap(6)
                    T("Phone and PC on the same Wi-Fi. The connection is encrypted and locked to the certificate in the QR.", 14, A.Text2)
                    VGap(16)
                    GlowButton("Scan QR code", Modifier.fillMaxWidth(), onClick = onScan)
                }
            }
        }
        if (canResume) item {
            Reveal(1) {
                Card(Modifier.edgeFade(listState, 3)) {
                    T("LAST COMPUTER", 11, A.Bright, FontWeight.Bold, 3f)
                    VGap(8)
                    T("Reconnect without scanning", 18, A.Text, FontWeight.Bold)
                    VGap(14)
                    GlowButton("Reconnect", Modifier.fillMaxWidth()) { vm.conn.resumeLast() }
                }
            }
        }
        item {
            Reveal(2) {
                Card(Modifier.edgeFade(listState, if (canResume) 4 else 3)) {
                    T("USB CABLE", 11, A.Bright, FontWeight.Bold, 3f)
                    VGap(8)
                    T("Most stable connection", 18, A.Text, FontWeight.Bold)
                    VGap(6)
                    T("Press \"Enable USB route\" in Blender, then enter the code it shows.", 14, A.Text2)
                    VGap(14)
                    Field(host, "localhost:47801", false) { host = it }
                    VGap(10)
                    Field(code, "Pairing code", true) { code = it.filter { c -> c.isDigit() || c == ' ' }.take(11) }
                    manualError?.let { VGap(8); T(it, 13, A.Rec) }
                    VGap(14)
                    GlowButton("Connect over USB", Modifier.fillMaxWidth()) {
                        val p = Protocol.parseManual(host, code)
                        if (p == null) manualError = "Use localhost:<port> and the 9-digit code" else { manualError = null; vm.connectQr(p) }
                    }
                }
            }
        }
        item {
            Reveal(3) {
                Card(Modifier.edgeFade(listState, if (canResume) 5 else 4)) {
                    T("CAN'T CONNECT?", 11, A.Warn, FontWeight.Bold, 3f)
                    VGap(8)
                    T("Same Wi-Fi, not a guest network. Allow Blender through Windows Firewall (Private). Or use the USB cable.", 14, A.Text2)
                }
            }
        }
    }
}
