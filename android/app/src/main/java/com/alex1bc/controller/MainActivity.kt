package com.alex1bc.controller

import android.os.Bundle
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.scaleIn
import androidx.compose.animation.scaleOut
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.animation.togetherWith
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.alex1bc.controller.net.LinkState
import com.alex1bc.controller.ui.Alex1bcTheme
import com.alex1bc.controller.ui.ConnectScreen
import com.alex1bc.controller.ui.ControllerScreen
import com.alex1bc.controller.ui.OnboardingScreen
import com.alex1bc.controller.ui.ScannerScreen
import com.alex1bc.controller.ui.SplashScreen

enum class Screen { Splash, Onboarding, Connect, Scanner, Controller }

class MainActivity : ComponentActivity() {
    private val vm: AppViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)      // never sleep mid-shot
        val bars = WindowInsetsControllerCompat(window, window.decorView)
        bars.hide(WindowInsetsCompat.Type.systemBars())
        bars.systemBarsBehavior = WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
        WindowCompat.setDecorFitsSystemWindows(window, false)
        setContent { Alex1bcTheme { App(vm) } }
    }
}

@Composable
fun App(vm: AppViewModel) {
    var screen by rememberSaveable { mutableStateOf(Screen.Splash) }
    val link by vm.conn.link.collectAsStateWithLifecycle()

    LaunchedEffect(link) {
        if (link is LinkState.Connected && (screen == Screen.Connect || screen == Screen.Scanner)) screen = Screen.Controller
    }
    BackHandler(enabled = screen == Screen.Scanner || screen == Screen.Controller) {
        if (screen == Screen.Controller) vm.conn.disconnect()
        screen = Screen.Connect
    }

    AnimatedContent(
        targetState = screen,
        transitionSpec = {
            val dir = if (targetState.ordinal > initialState.ordinal) 1 else -1
            (slideInHorizontally(tween(480, easing = FastOutSlowInEasing)) { it / 4 * dir } + fadeIn(tween(480)) + scaleIn(tween(480), initialScale = 0.94f)) togetherWith
                (slideOutHorizontally(tween(480, easing = FastOutSlowInEasing)) { -it / 4 * dir } + fadeOut(tween(300)) + scaleOut(tween(480), targetScale = 1.05f))
        },
        label = "nav",
    ) { s ->
        when (s) {
            Screen.Splash -> SplashScreen { screen = if (vm.prefs.onboarded) Screen.Connect else Screen.Onboarding }
            Screen.Onboarding -> OnboardingScreen { vm.finishOnboarding(); screen = Screen.Connect }
            Screen.Connect -> ConnectScreen(vm) { screen = Screen.Scanner }
            Screen.Scanner -> ScannerScreen(onPayload = { vm.connectQr(it) }, onBack = { screen = Screen.Connect })
            Screen.Controller -> ControllerScreen(vm) { vm.conn.disconnect(); screen = Screen.Connect }
        }
    }
}
