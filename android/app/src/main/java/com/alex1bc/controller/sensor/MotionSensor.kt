package com.alex1bc.controller.sensor

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager

/**
 * Phone orientation as a quaternion [w,x,y,z] (device -> world, world is Z-up like Blender).
 * Uses the game rotation vector (gyro + accelerometer, no magnetometer drift/noise); the add-on
 * aligns the heading on connect/HOME, so an arbitrary starting yaw is fine.
 */
class MotionSensor(context: Context) : SensorEventListener {
    private val manager = context.getSystemService(Context.SENSOR_SERVICE) as SensorManager
    private val sensor: Sensor? = manager.getDefaultSensor(Sensor.TYPE_GAME_ROTATION_VECTOR)
        ?: manager.getDefaultSensor(Sensor.TYPE_ROTATION_VECTOR)
    private val q = FloatArray(4)
    @Volatile private var stamp = 0L
    @Volatile private var running = false

    val available: Boolean get() = sensor != null

    fun start() {
        val s = sensor ?: return
        if (running) return
        running = manager.registerListener(this, s, 8_000)         // ~125 Hz requested, delivered as fast as the device allows
    }

    fun stop() {
        if (!running) return
        manager.unregisterListener(this)
        running = false
    }

    /** Latest orientation, or null if the sensor is silent for >0.5 s. */
    fun latest(): FloatArray? {
        if (!running || System.nanoTime() - stamp > 500_000_000L) return null
        return synchronized(q) { q.copyOf() }
    }

    override fun onSensorChanged(e: SensorEvent) {
        synchronized(q) { SensorManager.getQuaternionFromVector(q, e.values) }
        stamp = System.nanoTime()
    }

    override fun onAccuracyChanged(s: Sensor?, accuracy: Int) {}
}
