# Add project-specific ProGuard rules here.
# OkHttp: suppress warnings from Kotlin internals not shipped to end devices.
-dontwarn okhttp3.internal.**
-keep class okhttp3.** { *; }
-keepattributes Signature
-keepattributes *Annotation*
