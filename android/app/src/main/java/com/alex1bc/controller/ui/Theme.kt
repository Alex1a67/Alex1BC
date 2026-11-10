package com.alex1bc.controller.ui

import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.width
import androidx.compose.material3.LocalContentColor
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/** Official palette: midnight + electric blue. */
object A {
    val Bg = Color(0xFF090D17)
    val Bg2 = Color(0xFF101827)
    val Surf = Color(0xFF151F30)
    val Blue = Color(0xFF2479DC)
    val Bright = Color(0xFF73B9FF)
    val Text = Color(0xFFF4F7FC)
    val Text2 = Color(0xFFA7B4C9)
    val Rec = Color(0xFFFF4D5E)
    val Warn = Color(0xFFE0A030)
    val Ok = Color(0xFF3DDC97)
    val Line = Color(0x2973B9FF)
}

@Composable
fun Alex1bcTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = darkColorScheme(primary = A.Blue, background = A.Bg, surface = A.Surf, onSurface = A.Text, onBackground = A.Text)) {
        CompositionLocalProvider(LocalContentColor provides A.Text) { content() }
    }
}

@Composable
fun T(text: String, size: Int = 15, color: Color = A.Text, weight: FontWeight = FontWeight.Medium, spacing: Float = 0f,
      modifier: Modifier = Modifier, align: TextAlign? = null) {
    Text(text, modifier = modifier, color = color, fontSize = size.sp, fontWeight = weight, letterSpacing = spacing.sp, textAlign = align,
        lineHeight = (size * 1.35f).sp)
}

@Composable fun VGap(h: Int) = Spacer(Modifier.height(h.dp))
@Composable fun HGap(w: Int) = Spacer(Modifier.width(w.dp))
