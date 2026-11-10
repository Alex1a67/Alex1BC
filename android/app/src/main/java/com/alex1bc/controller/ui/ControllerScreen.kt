package com.alex1bc.controller.ui

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.*
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.*
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.*
import androidx.compose.runtime.snapshots.SnapshotStateList
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.alex1bc.controller.AppViewModel
import com.alex1bc.controller.net.LinkState
import com.alex1bc.controller.net.Toast
import kotlin.math.abs
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

private enum class Sheet { None, Cameras, Info }
private val MODES = listOf("gyro" to "GYRO", "hybrid" to "HYBRID", "analog" to "ANALOG")
private val LENSES = listOf(18, 24, 35, 50, 85, 135)

@Composable
fun ControllerScreen(vm: AppViewModel, onLeave: () -> Unit) {
    val st by vm.conn.state.collectAsStateWithLifecycle()
    val link by vm.conn.link.collectAsStateWithLifecycle()
    val rtt by vm.conn.rtt.collectAsStateWithLifecycle()
    val mode by vm.mode.collectAsStateWithLifecycle()
    val frozen by vm.frozen.collectAsStateWithLifecycle()
    var sheet by remember { mutableStateOf(Sheet.None) }
    val toasts: SnapshotStateList<Toast> = remember { mutableStateListOf() }

    LaunchedEffect(Unit) {
        vm.conn.toasts.collect { t ->
            toasts.add(t)
            launch { delay(2600); toasts.remove(t) }
        }
    }
    LaunchedEffect(mode) { if (mode != "analog" && !vm.hasSensor) toasts.add(Toast("No gyroscope found. Use ANALOG.", "error")) }

    Box(Modifier.fillMaxSize().background(A.Bg).windowInsetsPadding(WindowInsets.safeDrawing)) {
        BoxWithConstraints(Modifier.fillMaxSize().padding(horizontal = 14.dp, vertical = 8.dp)) {
            val landscape = maxWidth > maxHeight
            val stick: Dp = if (landscape) minOf(maxHeight * 0.62f, maxWidth * 0.26f) else minOf(maxWidth * 0.36f, maxHeight * 0.26f)
            Column(Modifier.fillMaxSize()) {
                TopBar(st.cam, st.lens, st.frame, link is LinkState.Connected, rtt, { sheet = Sheet.Cameras }, { sheet = Sheet.Info })
                val center: @Composable () -> Unit = {
                    CenterColumn(vm, mode, frozen, st.rec, st.recSeconds, st.playing, st.lens, landscape)
                }
                val left: @Composable () -> Unit = {
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        Joystick("MOVE", Modifier.size(stick)) { x, y -> vm.axes.mx = x; vm.axes.my = y }
                        VSlider("UP", Modifier.height(stick)) { vm.axes.mz = it }
                    }
                }
                val right: @Composable () -> Unit = {
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        VSlider("ZOOM", Modifier.height(stick)) { vm.axes.zoom = it }
                        Joystick("LOOK", Modifier.size(stick)) { x, y -> vm.axes.lx = x; vm.axes.ly = y }
                    }
                }
                if (landscape) {
                    Row(Modifier.weight(1f).fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) {
                        left(); Box(Modifier.weight(1f).padding(horizontal = 10.dp), contentAlignment = Alignment.Center) { center() }; right()
                    }
                } else {
                    Column(Modifier.weight(1f).fillMaxWidth(), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.SpaceEvenly) {
                        center()
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) { left(); right() }
                    }
                }
            }
        }

        // link banner / failure
        AnimatedVisibility(link !is LinkState.Connected && link !is LinkState.Failed, Modifier.align(Alignment.TopCenter).padding(top = 58.dp),
            enter = fadeIn() + slideInVertically { -it }, exit = fadeOut() + slideOutVertically { -it }) {
            Box(Modifier.clip(CircleShape).background(Color(0xFF3A2A10)).border(1.dp, A.Warn, CircleShape).padding(horizontal = 18.dp, vertical = 9.dp)) {
                T("Reconnecting to Blender...", 13, Color(0xFFFFD58A))
            }
        }
        AnimatedVisibility(link is LinkState.Failed, enter = fadeIn(), exit = fadeOut()) {
            Box(Modifier.fillMaxSize().background(Color(0xDD05080E)), contentAlignment = Alignment.Center) {
                Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.padding(30.dp)) {
                    T("Connection lost", 24, A.Text, FontWeight.Bold)
                    VGap(8)
                    T((link as? LinkState.Failed)?.message ?: "", 14, A.Text2, modifier = Modifier.widthIn(max = 420.dp))
                    VGap(18)
                    GlowButton("Back to connect", onClick = onLeave)
                }
            }
        }

        // toasts
        Column(Modifier.align(Alignment.BottomCenter).padding(bottom = 14.dp), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(8.dp)) {
            for (t in toasts) {
                Box(Modifier.clip(RoundedCornerShape(12.dp)).background(A.Surf).border(1.dp, when (t.level) { "error" -> A.Rec; "ok" -> A.Ok; else -> A.Line }, RoundedCornerShape(12.dp)).padding(horizontal = 16.dp, vertical = 10.dp)) { T(t.message, 14) }
            }
        }

        // sheets
        AnimatedVisibility(sheet != Sheet.None, enter = fadeIn(), exit = fadeOut()) {
            Box(Modifier.fillMaxSize().background(Color(0x99050810)).clickable(interactionSource = remember { androidx.compose.foundation.interaction.MutableInteractionSource() }, indication = null) { sheet = Sheet.None })
        }
        AnimatedVisibility(sheet != Sheet.None, Modifier.align(Alignment.BottomCenter), enter = slideInVertically(spring(dampingRatio = 0.8f, stiffness = 400f)) { it } + fadeIn(),
            exit = slideOutVertically { it } + fadeOut()) {
            val shape = RoundedCornerShape(topStart = 24.dp, topEnd = 24.dp)
            Column(Modifier.widthIn(max = 460.dp).fillMaxWidth().clip(shape).background(A.Bg2).border(1.dp, A.Line, shape).padding(18.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                if (sheet == Sheet.Cameras) {
                    T("CAMERA", 11, A.Bright, FontWeight.Bold, 3f)
                    if (st.cams.isEmpty()) T("No cameras in the scene. Add one in Blender.", 15, A.Text2)
                    for (n in st.cams) {
                        Box(Modifier.fillMaxWidth().clip(RoundedCornerShape(14.dp)).background(if (n == st.cam) A.Blue.copy(alpha = 0.25f) else A.Surf)
                            .clickable { vm.conn.cmd("camera", n); sheet = Sheet.None }.padding(16.dp)) { T(n, 16) }
                    }
                } else if (sheet == Sheet.Info) {
                    T("CONNECTION", 11, A.Bright, FontWeight.Bold, 3f)
                    T("Latency: $rtt ms", 15); T("Blender: ${st.blender.ifEmpty { "-" }}", 15); T("Takes in file: ${st.takes}", 15)
                    T("Gyroscope: ${if (vm.hasSensor) "available" else "not found"}", 15)
                    VGap(6)
                    GlowButton("Disconnect", Modifier.fillMaxWidth()) { sheet = Sheet.None; vm.conn.disconnect(); onLeave() }
                }
            }
        }
    }
}

@Composable
private fun TopBar(cam: String?, lens: Float, frame: Int, linked: Boolean, rtt: Int, onCam: () -> Unit, onInfo: () -> Unit) {
    Row(Modifier.fillMaxWidth().height(46.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        LensMark(Modifier.size(24.dp))
        T("Alex1BC", 15, A.Text, FontWeight.Bold, 1f)
        Spacer(Modifier.weight(1f))
        Row(Modifier.clip(CircleShape).background(A.Surf).border(1.dp, A.Line, CircleShape).clickable { onCam() }.padding(horizontal = 14.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically) {
            T(cam ?: "No camera", 14, modifier = Modifier.widthIn(max = 160.dp)); HGap(6)
            Canvas(Modifier.size(14.dp)) { iconChevron(A.Text2) }
        }
        T("${lens.toInt()} mm", 15, A.Text, FontWeight.Bold)
        T("f $frame", 13, A.Text2)
        val dot by animateColorAsState(if (linked) A.Ok else A.Warn, tween(300), label = "dot")
        Row(Modifier.clip(CircleShape).clickable { onInfo() }.padding(6.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.size(10.dp).clip(CircleShape).background(dot)); HGap(6); T(if (linked) "$rtt ms" else "--", 12, A.Text2)
        }
    }
}

@Composable
private fun CenterColumn(vm: AppViewModel, mode: String, frozen: Boolean, rec: String, recSeconds: Float, playing: Boolean, lens: Float, landscape: Boolean) {
    val s = recSeconds.toInt()
    val recLabel = if (rec == "off") "REC" else "%02d:%02d".format(s / 60, s % 60)
    Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(if (landscape) 8.dp else 12.dp)) {
        ModeSwitch(MODES, mode, Modifier.widthIn(max = 300.dp).fillMaxWidth()) { vm.setMode(it) }
        RecButton(rec, recLabel) { vm.conn.cmd("rec") }
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            ActionButton(if (rec != "off") (if (playing) "PAUSE" else "RESUME") else (if (playing) "PAUSE" else "PLAY"), active = playing, onClick = { vm.conn.cmd("play") }) { c ->
                if (playing) iconPause(c) else iconPlay(c)
            }
            ActionButton("KEY", onClick = { vm.conn.cmd("key") }) { c -> iconKey(c) }
            ActionButton("HOME", onClick = { vm.conn.cmd("recenter") }) { c -> iconHome(c) }
            ActionButton("HOLD", active = frozen, danger = true, onClick = { vm.toggleFreeze() }) { c -> iconHold(c) }
        }
        if (landscape) Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            for (mm in LENSES) {
                val on = abs(lens - mm) < 1f
                Box(Modifier.clip(RoundedCornerShape(10.dp)).background(if (on) A.Blue.copy(alpha = 0.25f) else A.Bg2).border(1.dp, if (on) A.Blue else A.Line, RoundedCornerShape(10.dp))
                    .clickable { vm.conn.cmd("lens", mm.toFloat()) }.padding(horizontal = 10.dp, vertical = 7.dp)) { T("$mm", 12, if (on) A.Text else A.Text2) }
            }
        }
    }
}
