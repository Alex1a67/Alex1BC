package com.alex1bc.controller.ui

import androidx.compose.animation.core.*
import androidx.compose.foundation.*
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.*
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp

/** The Alex1BC lens mark: aperture blades that can rotate and glow. */
@Composable
fun LensMark(modifier: Modifier = Modifier, rotation: Float = 0f, glow: Float = 1f) {
    Canvas(modifier) {
        val c = center
        val r = size.minDimension / 2f
        drawCircle(A.Blue.copy(alpha = 0.16f * glow), r)
        drawCircle(A.Blue, r * 0.92f, style = Stroke(r * 0.05f))
        drawCircle(A.Line, r * 0.66f, style = Stroke(r * 0.02f))
        rotate(rotation, c) {
            for (i in 0 until 6) rotate(i * 60f, c) {
                val p = Path().apply {
                    moveTo(c.x, c.y - r * 0.20f); lineTo(c.x + r * 0.24f, c.y - r * 0.64f); lineTo(c.x - r * 0.06f, c.y - r * 0.64f); close()
                }
                drawPath(p, A.Bright.copy(alpha = 0.9f))
            }
        }
        drawCircle(A.Bright, r * 0.10f)
    }
}

/** Big thumb stick. Reports x right / y up in -1..1; springs back when released. */
@Composable
fun Joystick(label: String, modifier: Modifier = Modifier, onChange: (Float, Float) -> Unit) {
    var padSize by remember { mutableStateOf(IntSize.Zero) }
    var target by remember { mutableStateOf(Offset.Zero) }
    var active by remember { mutableStateOf(false) }
    val shown by animateOffsetAsState(target, if (active) snap<Offset>() else spring<Offset>(dampingRatio = 0.45f, stiffness = 380f), label = "knob")
    val glow by animateFloatAsState(if (active) 1f else 0f, tween(200), label = "glow")
    val haptic = LocalHapticFeedback.current
    Box(
        modifier.aspectRatio(1f).onSizeChanged { padSize = it }.pointerInput(Unit) {
            awaitEachGesture {
                val down = awaitFirstDown()
                active = true
                haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                fun upd(p: Offset) {
                    val r = padSize.width / 2f * 0.62f
                    val v = (p - Offset(padSize.width / 2f, padSize.height / 2f)) / r
                    val len = v.getDistance()
                    val n = if (len > 1f) v / len else v
                    target = n
                    onChange(n.x, -n.y)
                }
                upd(down.position)
                do {
                    val ev = awaitPointerEvent()
                    val ch = ev.changes.firstOrNull { it.id == down.id }
                    if (ch != null && ch.pressed) { upd(ch.position); ch.consume() }
                } while (ev.changes.any { it.id == down.id && it.pressed })
                active = false; target = Offset.Zero; onChange(0f, 0f)
            }
        },
        contentAlignment = Alignment.BottomCenter,
    ) {
        Canvas(Modifier.fillMaxSize()) {
            val c = center
            val rad = size.minDimension / 2f
            drawCircle(Brush.radialGradient(listOf(A.Surf, A.Bg2)), rad)
            if (glow > 0f) drawCircle(A.Blue.copy(alpha = 0.14f * glow), rad + 12f * glow)
            drawCircle(lerp(A.Line, A.Blue, glow), rad - 1f, style = Stroke(2.5f))
            drawLine(A.Line, Offset(c.x, c.y - rad * 0.7f), Offset(c.x, c.y + rad * 0.7f), 2f)
            drawLine(A.Line, Offset(c.x - rad * 0.7f, c.y), Offset(c.x + rad * 0.7f, c.y), 2f)
            val kr = rad * 0.38f
            val k = c + Offset(shown.x * rad * 0.62f, shown.y * rad * 0.62f)
            drawCircle(Brush.radialGradient(listOf(A.Bright, A.Blue), center = k - Offset(kr * 0.3f, kr * 0.3f), radius = kr * 1.5f), kr, k)
        }
        T(label, 10, A.Text2, spacing = 3f, modifier = Modifier.padding(bottom = 14.dp))
    }
}

/** Vertical spring slider (rise/lower, zoom). Reports -1..1, up positive. */
@Composable
fun VSlider(label: String, modifier: Modifier = Modifier, onChange: (Float) -> Unit) {
    var sliderSize by remember { mutableStateOf(IntSize.Zero) }
    var target by remember { mutableFloatStateOf(0f) }
    var active by remember { mutableStateOf(false) }
    val shown by animateFloatAsState(target, if (active) snap<Float>() else spring<Float>(dampingRatio = 0.5f, stiffness = 420f), label = "vs")
    val glow by animateFloatAsState(if (active) 1f else 0f, tween(200), label = "vsg")
    val haptic = LocalHapticFeedback.current
    Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = modifier) {
        Box(Modifier.weight(1f).width(48.dp).onSizeChanged { sliderSize = it }.pointerInput(Unit) {
            awaitEachGesture {
                val down = awaitFirstDown()
                active = true
                haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                fun upd(p: Offset) {
                    val half = (sliderSize.height - 40.dp.toPx()) / 2f
                    val v = (-(p.y - sliderSize.height / 2f) / half).coerceIn(-1f, 1f)
                    target = v; onChange(v)
                }
                upd(down.position)
                do {
                    val ev = awaitPointerEvent()
                    val ch = ev.changes.firstOrNull { it.id == down.id }
                    if (ch != null && ch.pressed) { upd(ch.position); ch.consume() }
                } while (ev.changes.any { it.id == down.id && it.pressed })
                active = false; target = 0f; onChange(0f)
            }
        }) {
            Canvas(Modifier.fillMaxSize()) {
                drawRoundRect(A.Bg2, cornerRadius = CornerRadius(size.width / 2f))
                drawRoundRect(lerp(A.Line, A.Blue, glow), cornerRadius = CornerRadius(size.width / 2f), style = Stroke(2.5f))
                drawLine(A.Line, Offset(size.width * 0.3f, size.height / 2f), Offset(size.width * 0.7f, size.height / 2f), 2f)
                val half = (size.height - 40.dp.toPx()) / 2f
                drawCircle(Brush.radialGradient(listOf(A.Bright, A.Blue), center = Offset(size.width / 2f - 5f, size.height / 2f - shown * half - 5f), radius = 30f),
                    19.dp.toPx(), Offset(size.width / 2f, size.height / 2f - shown * half))
            }
        }
        VGap(6)
        T(label, 10, A.Text2, spacing = 3f)
    }
}

@Composable
fun ModeSwitch(modes: List<Pair<String, String>>, selected: String, modifier: Modifier = Modifier, onSelect: (String) -> Unit) {
    val shape = RoundedCornerShape(14.dp)
    BoxWithConstraints(modifier.height(46.dp).clip(shape).background(A.Bg2).border(1.dp, A.Line, shape).padding(4.dp)) {
        val w = maxWidth / modes.size
        val x by animateDpAsState(w * modes.indexOfFirst { it.first == selected }.coerceAtLeast(0), spring(dampingRatio = 0.7f, stiffness = 500f), label = "thumb")
        Box(Modifier.offset(x = x).width(w).fillMaxHeight().clip(RoundedCornerShape(10.dp)).background(A.Blue))
        Row(Modifier.fillMaxSize()) {
            for ((id, label) in modes) {
                Box(
                    Modifier.weight(1f).fillMaxHeight().clickable(interactionSource = remember { MutableInteractionSource() }, indication = null) { onSelect(id) },
                    contentAlignment = Alignment.Center,
                ) { T(label, 12, if (id == selected) A.Text else A.Text2, FontWeight.Bold, 1.4f) }
            }
        }
    }
}

@Composable
fun RecButton(rec: String, label: String, onClick: () -> Unit) {
    val inf = rememberInfiniteTransition(label = "rec")
    val pulse by inf.animateFloat(0f, 1f, infiniteRepeatable(tween(1200, easing = FastOutSlowInEasing), RepeatMode.Restart), label = "p")
    val core by animateFloatAsState(if (rec == "off") 0.6f else 0.34f, spring(dampingRatio = 0.6f), label = "core")
    val round by animateFloatAsState(if (rec == "off") 1f else 0.3f, tween(250), label = "round")
    val haptic = LocalHapticFeedback.current
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Canvas(Modifier.size(100.dp).clip(CircleShape).clickable { haptic.performHapticFeedback(HapticFeedbackType.LongPress); onClick() }) {
            val c = center
            val rad = size.minDimension / 2f
            val col = if (rec == "pause") A.Warn else A.Rec
            drawCircle(if (rec == "off") A.Text2 else col, rad - 4f, style = Stroke(6f))
            if (rec == "rec") drawCircle(A.Rec.copy(alpha = 0.4f * (1f - pulse)), rad + 14f * pulse, style = Stroke(5f))
            val cr = rad * core
            drawRoundRect(if (rec == "pause") A.Warn else A.Rec, Offset(c.x - cr, c.y - cr), Size(cr * 2, cr * 2), CornerRadius(cr * round))
        }
        VGap(6)
        T(label, 12, if (rec == "off") A.Text2 else A.Text, FontWeight.Bold, 1.5f)
    }
}

@Composable
fun ActionButton(label: String, modifier: Modifier = Modifier, active: Boolean = false, danger: Boolean = false,
                 onClick: () -> Unit, icon: DrawScope.(Color) -> Unit) {
    val src = remember { MutableInteractionSource() }
    val pressed by src.collectIsPressedAsState()
    val scale by animateFloatAsState(if (pressed) 0.9f else 1f, spring(stiffness = 900f), label = "bs")
    val haptic = LocalHapticFeedback.current
    val accent = if (danger) A.Rec else A.Blue
    val shape = RoundedCornerShape(16.dp)
    Column(
        modifier.size(60.dp).graphicsLayer { scaleX = scale; scaleY = scale }.clip(shape)
            .background(if (active) accent.copy(alpha = 0.22f) else A.Surf).border(1.dp, if (active) accent else A.Line, shape)
            .clickable(interactionSource = src, indication = null) { haptic.performHapticFeedback(HapticFeedbackType.LongPress); onClick() },
        horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center,
    ) {
        Canvas(Modifier.size(22.dp)) { icon(if (active) A.Bright else A.Text) }
        VGap(3)
        T(label, 9, A.Text2, spacing = 1.4f)
    }
}

@Composable
fun GlowButton(text: String, modifier: Modifier = Modifier, enabled: Boolean = true, onClick: () -> Unit) {
    val src = remember { MutableInteractionSource() }
    val pressed by src.collectIsPressedAsState()
    val scale by animateFloatAsState(if (pressed) 0.96f else 1f, spring(stiffness = 800f), label = "gs")
    val shape = RoundedCornerShape(18.dp)
    Box(
        modifier.graphicsLayer { scaleX = scale; scaleY = scale; alpha = if (enabled) 1f else 0.5f }
            .shadow(18.dp, shape, ambientColor = A.Blue, spotColor = A.Blue).clip(shape)
            .background(Brush.horizontalGradient(listOf(A.Blue, Color(0xFF3B93F0))))
            .clickable(interactionSource = src, indication = null, enabled = enabled) { onClick() }
            .padding(horizontal = 26.dp, vertical = 16.dp),
        contentAlignment = Alignment.Center,
    ) { T(text, 16, A.Text, FontWeight.Bold, 1f) }
}

// ---- icons (drawn, no icon library needed)
fun DrawScope.iconPlay(c: Color) { val p = Path().apply { moveTo(size.width * .28f, size.height * .12f); lineTo(size.width * .9f, size.height * .5f); lineTo(size.width * .28f, size.height * .88f); close() }; drawPath(p, c) }
fun DrawScope.iconPause(c: Color) { val w = size.width; val h = size.height; drawRoundRect(c, Offset(w * .2f, h * .12f), Size(w * .2f, h * .76f), CornerRadius(3f)); drawRoundRect(c, Offset(w * .6f, h * .12f), Size(w * .2f, h * .76f), CornerRadius(3f)) }
fun DrawScope.iconKey(c: Color) { val w = size.width; val h = size.height; val p = Path().apply { moveTo(w / 2, 0f); lineTo(w, h / 2); lineTo(w / 2, h); lineTo(0f, h / 2); close() }; drawPath(p, c, style = Stroke(3f, join = StrokeJoin.Round)); drawCircle(c, 3f) }
fun DrawScope.iconHome(c: Color) { val w = size.width; val h = size.height; drawCircle(c, w * .16f, style = Stroke(3f)); drawLine(c, Offset(w / 2, 0f), Offset(w / 2, h * .28f), 3f); drawLine(c, Offset(w / 2, h * .72f), Offset(w / 2, h), 3f); drawLine(c, Offset(0f, h / 2), Offset(w * .28f, h / 2), 3f); drawLine(c, Offset(w * .72f, h / 2), Offset(w, h / 2), 3f) }
fun DrawScope.iconHold(c: Color) { drawRoundRect(c, Offset(size.width * .18f, size.height * .18f), Size(size.width * .64f, size.height * .64f), CornerRadius(5f), style = Stroke(3f)) }
fun DrawScope.iconChevron(c: Color) { val p = Path().apply { moveTo(size.width * .2f, size.height * .35f); lineTo(size.width / 2, size.height * .65f); lineTo(size.width * .8f, size.height * .35f) }; drawPath(p, c, style = Stroke(3f, cap = StrokeCap.Round, join = StrokeJoin.Round)) }
