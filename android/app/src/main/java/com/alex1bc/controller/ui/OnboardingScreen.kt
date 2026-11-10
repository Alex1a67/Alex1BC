package com.alex1bc.controller.ui

import androidx.compose.animation.core.*
import androidx.compose.foundation.*
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.*
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.sin
import kotlinx.coroutines.launch

private data class Page(val title: String, val body: String)

private val PAGES = listOf(
    Page("Scan to connect", "Start Alex1BC in Blender and scan its QR code. No typing, and the link is locked to your computer."),
    Page("Move like a camera", "Tilt and turn your phone and the Blender camera follows. Add the joysticks to dolly, rise and zoom."),
    Page("Record the take", "One tap records your performance and turns it into editable Blender keyframes. Nothing is overwritten."),
)

@Composable
fun OnboardingScreen(onDone: () -> Unit) {
    val pager = rememberPagerState(pageCount = { PAGES.size })
    val scope = rememberCoroutineScope()
    val last = pager.currentPage == PAGES.size - 1
    Column(Modifier.fillMaxSize().background(A.Bg).windowInsetsPadding(WindowInsets.safeDrawing).padding(horizontal = 24.dp, vertical = 14.dp)) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
            T("SKIP", 12, A.Text2, FontWeight.Bold, 2f, Modifier.clickable { onDone() }.padding(10.dp))
        }
        HorizontalPager(pager, Modifier.weight(1f)) { page ->
            val offset = (pager.currentPage - page) + pager.currentPageOffsetFraction
            val dens = LocalDensity.current.density
            BoxWithConstraints(Modifier.fillMaxSize()) {
                val wide = maxWidth > maxHeight
                val art = @Composable {
                    Illustration(page, Modifier.size(if (wide) minOf(maxHeight, 260.dp) else 240.dp).graphicsLayer {
                        translationX = offset * size.width * 0.5f
                        alpha = 1f - abs(offset) * 0.8f
                        rotationY = offset * 28f
                        cameraDistance = 14f * dens
                    })
                }
                val text = @Composable {
                    Column(
                        Modifier.graphicsLayer { translationX = offset * 90f; alpha = 1f - abs(offset) },
                        horizontalAlignment = if (wide) Alignment.Start else Alignment.CenterHorizontally,
                    ) {
                        T("0${page + 1}", 12, A.Bright, FontWeight.Bold, 4f)
                        VGap(8)
                        T(PAGES[page].title, 30, A.Text, FontWeight.Bold)
                        VGap(10)
                        T(PAGES[page].body, 16, A.Text2, align = if (wide) TextAlign.Start else TextAlign.Center, modifier = Modifier.widthIn(max = 380.dp))
                    }
                }
                if (wide) Row(Modifier.fillMaxSize(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceEvenly) { art(); text() }
                else Column(Modifier.fillMaxSize(), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) { art(); VGap(24); text() }
            }
        }
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                for (i in PAGES.indices) {
                    val w by animateDpAsState(if (i == pager.currentPage) 28.dp else 8.dp, spring(dampingRatio = 0.7f), label = "dot")
                    Box(Modifier.height(8.dp).width(w).clip(CircleShape).background(if (i == pager.currentPage) A.Blue else A.Line))
                }
            }
            GlowButton(if (last) "Get started" else "Next") {
                if (last) onDone() else scope.launch { pager.animateScrollToPage(pager.currentPage + 1) }
            }
        }
    }
}

@Composable
private fun Illustration(kind: Int, modifier: Modifier) {
    val inf = rememberInfiniteTransition(label = "ill")
    val t by inf.animateFloat(0f, 1f, infiniteRepeatable(tween(2600, easing = LinearEasing)), label = "t")
    Canvas(modifier) {
        val w = size.width
        val h = size.height
        val wave = sin(t * 2f * PI.toFloat())
        when (kind) {
            0 -> {                                              // QR grid with a scan line
                val n = 9
                val cell = w / (n + 2)
                val pattern = "111010111" + "100010101" + "101110111" + "000101000" + "110111011" + "010001010" + "111010111" + "101001001" + "111011101"
                val lineY = t * h
                for (i in 0 until n * n) if (pattern[i] == '1') {
                    val cx = cell + (i % n) * cell
                    val cy = cell + (i / n) * cell
                    val near = 1f - minOf(1f, abs(cy + cell / 2 - lineY) / (cell * 2.5f))
                    drawRoundRect(A.Bright.copy(alpha = 0.25f + 0.75f * near), Offset(cx + 2f, cy + 2f), Size(cell - 4f, cell - 4f), CornerRadius(4f))
                }
                drawRect(Brush.verticalGradient(listOf(Color.Transparent, A.Blue.copy(alpha = 0.55f), Color.Transparent), lineY - 30f, lineY + 30f), Offset(0f, lineY - 30f), Size(w, 60f))
            }
            1 -> {                                              // phone tilts, camera mirrors it
                val py = h / 2f
                rotate(wave * 20f, Offset(w * 0.22f, py)) {
                    drawRoundRect(A.Surf, Offset(w * 0.22f - w * 0.09f, py - h * 0.2f), Size(w * 0.18f, h * 0.4f), CornerRadius(18f))
                    drawRoundRect(A.Bright, Offset(w * 0.22f - w * 0.09f, py - h * 0.2f), Size(w * 0.18f, h * 0.4f), CornerRadius(18f), style = Stroke(4f))
                }
                for (i in 0 until 6) {
                    val f = (t + i / 6f) % 1f
                    drawCircle(A.Blue.copy(alpha = sin(f * PI.toFloat())), 6f, Offset(w * 0.34f + f * w * 0.3f, py))
                }
                rotate(wave * 20f, Offset(w * 0.78f, py)) {
                    drawRoundRect(A.Surf, Offset(w * 0.78f - w * 0.14f, py - h * 0.11f), Size(w * 0.28f, h * 0.22f), CornerRadius(14f))
                    drawCircle(A.Blue, h * 0.08f, Offset(w * 0.78f + w * 0.14f, py))
                    drawCircle(A.Bright, h * 0.035f, Offset(w * 0.78f + w * 0.14f, py))
                }
            }
            else -> {                                           // record + keyframes
                val pulse = (t * 1.6f) % 1f
                drawCircle(A.Rec.copy(alpha = 0.35f * (1f - pulse)), h * 0.2f + pulse * h * 0.12f, Offset(w / 2, h * 0.34f), style = Stroke(5f))
                drawCircle(A.Rec, h * 0.14f, Offset(w / 2, h * 0.34f))
                drawLine(A.Line, Offset(w * 0.08f, h * 0.78f), Offset(w * 0.92f, h * 0.78f), 4f)
                val shown = (t * 6f).toInt()
                for (i in 0..4) {
                    val x = w * (0.14f + i * 0.18f)
                    val s = if (i < shown) 1f else 0.3f
                    val p = Path().apply { moveTo(x, h * 0.78f - 16f * s); lineTo(x + 16f * s, h * 0.78f); lineTo(x, h * 0.78f + 16f * s); lineTo(x - 16f * s, h * 0.78f); close() }
                    drawPath(p, if (i < shown) A.Bright else A.Line)
                }
            }
        }
    }
}
