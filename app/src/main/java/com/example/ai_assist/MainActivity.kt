package com.example.ai_assist

import android.Manifest
import android.os.Bundle
import android.os.Handler
import android.os.HandlerThread
import android.text.Spannable
import android.text.SpannableString
import android.text.style.RelativeSizeSpan
import android.text.style.TypefaceSpan
import android.util.Log
import android.view.View
import android.view.animation.AlphaAnimation
import android.view.animation.Animation
import androidx.activity.result.contract.ActivityResultContracts
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import com.example.ai_assist.databinding.ActivityMainBinding
import com.example.ai_assist.repository.ChatRepository
import com.example.ai_assist.service.GameApiService
import com.example.ai_assist.service.RayNeoDeviceManager
import com.example.ai_assist.viewmodel.ChatViewModel
import com.example.ai_assist.viewmodel.ChatViewModelFactory
import com.example.ai_assist.utils.RayNeoAudioRecorder
import com.example.ai_assist.utils.MahjongMapper
import com.ffalcon.mercury.android.sdk.touch.TempleAction
import com.ffalcon.mercury.android.sdk.ui.activity.BaseMirrorActivity
import kotlinx.coroutines.launch
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

class MainActivity : BaseMirrorActivity<ActivityMainBinding>() {

    private lateinit var viewModel: ChatViewModel
    private lateinit var cameraExecutor: ExecutorService

    private lateinit var backHandler: Handler
    private lateinit var backHandlerThread: HandlerThread
    
    // Audio Recorder
    private var audioRecorder: RayNeoAudioRecorder? = null

    // Game State Management
    enum class Step { TAKE_PHOTO, START_VOICE, STOP_VOICE }
    private var currentStep = Step.TAKE_PHOTO
    
    private val requestPermissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { _ -> }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        cameraExecutor = Executors.newSingleThreadExecutor()
        backHandlerThread = HandlerThread("background")
        backHandlerThread.start()
        backHandler = Handler(backHandlerThread.looper)

        setupDependencies()
        setupUI()
        checkPermissions()
        observeViewModel()
        observeTempleActions()
        
        updateStepUI()
    }

    private fun setupDependencies() {
        val retrofit = Retrofit.Builder()
            .baseUrl(AppConfig.SERVER_BASE_URL)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
        val apiService = retrofit.create(GameApiService::class.java)
        val repository = ChatRepository(apiService)
        val deviceManager = RayNeoDeviceManager(this)
        val factory = ChatViewModelFactory(repository, deviceManager)
        viewModel = ViewModelProvider(this, factory)[ChatViewModel::class.java]
        
        audioRecorder = RayNeoAudioRecorder(this) { file ->
            viewModel.uploadAudio(file)
        }
    }

    private fun setupUI() {
        mBindingPair.updateView { 
            tvStatus.text = "已连接"
            tvContentHand.text = ""
            tvContentSuggested.text = ""
            tvContentWaiting.text = ""
        }
    }

    private fun observeViewModel() {
        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                viewModel.mappedResult.collect { result ->
                    result?.let {
                        updateResultUI(
                            hand = it.userHand.joinToString(" "),
                            melded = it.meldedTiles.joinToString(" "),
                            suggested = it.suggestedPlay
                        )
                        // After photo results are back, prompt for voice
                        if (currentStep == Step.TAKE_PHOTO) {
                            currentStep = Step.START_VOICE
                            updateStepUI()
                        }
                    }
                }
            }
        }

        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                viewModel.isAnalyzing.collect { isAnalyzing ->
                    if (isAnalyzing) {
                        mBindingPair.updateView {
                            tvStatus.text = "正在识别中..."
                        }
                    }
                }
            }
        }
    }

    private fun observeTempleActions() {
        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                templeActionViewModel.state.collect { action ->
                    Log.d("MainActivity", "Received TempleAction: $action")
                    when (action) {
                        is TempleAction.DoubleClick -> {
                            if (currentStep == Step.TAKE_PHOTO) {
                                viewModel.takePhoto()
                                mBindingPair.updateView { tvStatus.text = "拍摄中..." }
                            }
                        }
                        is TempleAction.SlideForward -> {
                            if (currentStep == Step.START_VOICE) {
                                audioRecorder?.start()
                                currentStep = Step.STOP_VOICE
                                updateStepUI()
                            }
                        }
                        is TempleAction.SlideBackward -> {
                            if (currentStep == Step.STOP_VOICE) {
                                audioRecorder?.stop()
                                // Cycle back to take photo for next turn
                                currentStep = Step.TAKE_PHOTO
                                updateStepUI()
                            }
                        }
                        else -> {}
                    }
                }
            }
        }
    }

    private fun updateStepUI() {
        mBindingPair.updateView {
            when (currentStep) {
                Step.TAKE_PHOTO -> {
                    tvStatus.text = "双击拍照"
                }
                Step.START_VOICE -> {
                    tvStatus.text = "滑动开启语音识别"
                }
                Step.STOP_VOICE -> {
                    tvStatus.text = "滑动关闭语音识别"
                }
            }
        }
    }

    private fun updateResultUI(hand: String, melded: String, suggested: String) {
        mBindingPair.updateView {
            tvContentHand.text = formatMahjongText(hand)
            tvContentSuggested.text = if (melded.isNotEmpty()) "吃碰杠: $melded" else ""
            tvContentWaiting.text = formatMahjongText("建议出牌: $suggested")
            startHighlightAnimation()
        }
    }

    private fun startHighlightAnimation() {
        mBindingPair.updateView {
            val anim = AlphaAnimation(0.5f, 1.0f)
            anim.duration = 500
            anim.repeatMode = Animation.REVERSE
            anim.repeatCount = 3
            tvContentWaiting.startAnimation(anim)
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        audioRecorder?.stop()
        cameraExecutor.shutdown()
        backHandlerThread.quitSafely()
    }

    private fun checkPermissions() {
        requestPermissionLauncher.launch(arrayOf(Manifest.permission.CAMERA, Manifest.permission.RECORD_AUDIO))
    }

    private fun formatMahjongText(originalText: String): SpannableString {
        val spannable = SpannableString(originalText)
        val mahjongTypeface = try { resources.getFont(R.font.mahjong_color) } catch (e: Exception) { null }
        val scaleFactor = if (AppConfig.USE_COLOR_FONT) AppConfig.FONT_SCALE_COLOR else AppConfig.FONT_SCALE_DEFAULT
        var index = 0
        while (index < originalText.length) {
            val codePoint = originalText.codePointAt(index)
            val charCount = Character.charCount(codePoint)
            if (codePoint in 0x1F000..0x1F02B) {
                spannable.setSpan(RelativeSizeSpan(scaleFactor), index, index + charCount, Spannable.SPAN_EXCLUSIVE_EXCLUSIVE)
                if (mahjongTypeface != null) {
                    spannable.setSpan(TypefaceSpan(mahjongTypeface), index, index + charCount, Spannable.SPAN_EXCLUSIVE_EXCLUSIVE)
                }
            }
            index += charCount
        }
        return spannable
    }
}
