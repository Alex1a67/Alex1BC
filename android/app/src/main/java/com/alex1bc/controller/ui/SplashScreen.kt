package com.alex1bc.controller.ui

import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.delay

@Composable
fun SplashScreen(onDone: () -> Unit) {
    val inf = rememberInfiniteTransition(label = "splash")
    val rot by inf.animateFloat(0f, 360f, infiniteRepeatable(tween(5000, easing = LinearEasing)), label = "rot")
    val appear = remember { Animatable(0f) }
    LaunchedEffect(Unit) {
        appear.animateTo(1f, tween(900, easing = FastOutSlowInEasing))
        delay(1000)
        onDone()
    }
    Column(Modifier.fillMaxSize().background(A.Bg), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) {
        LensMark(
            Modifier.size(150.dp).graphicsLayer { val s = 0.55f + 0.45f * appear.value; scaleX = s; scaleY = s; alpha = appear.value },
            rotation = rot * 0.4f, glow = 0.6f + 0.4f * appear.value,
        )
        VGap(22)
        T("Alex1BC", 34, A.Text, FontWeight.Bold, 2f, Modifier.graphicsLayer { alpha = appear.value; translationY = (1f - appear.value) * 30f })
        VGap(6)
        T("YOUR CAMERA. YOUR MOVEMENT.", 11, A.Bright, FontWeight.Medium, 4f, Modifier.graphicsLayer { alpha = appear.value })
    }
}
