"""
ASR（语音转文本）和 TTS（文本转语音）API 路由
使用硅基流动的 OpenAI 兼容接口
"""
from typing import Optional

import httpx
from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from chatchat.server.utils import BaseResponse, get_model_info
from chatchat.utils import build_logger

logger = build_logger()

# 创建路由
asr_tts_router = APIRouter(prefix="/asr_tts", tags=["ASR/TTS 语音功能"])

# OpenAI 标准音色到 SiliconFlow CosyVoice2 格式的映射
OPENAI_TO_SILICONFLOW_VOICE = {
    "alloy": "alex",
    "echo": "echo",
    "shimmer": "shimmer",
    "fable": "fable",
    "onyx": "onyx",
    "nova": "nova",
    "ash": "ash",
    "ballad": "ballad",
    "coral": "coral",
    "sage": "sage",
    "verse": "verse",
}


class TTSRequest(BaseModel):
    """TTS 请求模型"""
    text: str
    model: str = "FunAudioLLM/CosyVoice2-0.5B"
    voice: str = "FunAudioLLM/CosyVoice2-0.5B:alex"  # 音色格式：模型名:音色名
    speed: float = 1.0  # 0.25 - 4.0
    response_format: str = "mp3"  # mp3, opus, wav, pcm


@asr_tts_router.post("/asr/transcribe", response_model=BaseResponse, summary="语音转文本（ASR）")
async def asr_transcribe(
    file: UploadFile = File(..., description="音频文件"),
    model: str = Form("FunAudioLLM/SenseVoiceSmall", description="ASR 模型名称"),
    language: str = Form("auto", description="语言代码，auto 表示自动检测"),
):
    """
    调用硅基流动 ASR 模型，将语音转为文本
    
    支持的音频格式：wav, mp3, m4a, flac, ogg
    
    Args:
        file: 上传的音频文件
        model: ASR 模型名称，默认 FunAudioLLM/SenseVoiceSmall
        language: 语言代码，默认 auto 自动检测
        
    Returns:
        BaseResponse: 包含识别文本的响应
    """
    try:
        # 获取模型配置信息
        model_info = get_model_info(model_name=model, platform_name="siliconflow")
        if not model_info:
            logger.error(f"未找到 ASR 模型配置: {model}")
            return BaseResponse(code=404, msg=f"未找到 ASR 模型 {model}")
        
        api_base_url = model_info.get("api_base_url")
        api_key = model_info.get("api_key")
        
        logger.info(f"正在调用 ASR 模型: {model}, 文件: {file.filename}")
        
        # 读取上传的音频文件
        audio_content = await file.read()
        
        # 调用硅基流动的 ASR 接口（OpenAI 兼容）
        # 接口路径：/v1/audio/transcriptions
        url = f"{api_base_url}/audio/transcriptions"
        
        files = {
            "file": (file.filename, audio_content, file.content_type or "audio/wav")
        }
        data = {
            "model": model,
        }
        if language and language != "auto":
            data["language"] = language
            
        headers = {
            "Authorization": f"Bearer {api_key}"
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, files=files, data=data, headers=headers)
            response.raise_for_status()
            result = response.json()
        
        # 硅基流动返回格式：{"text": "识别结果"}
        text = result.get("text", "")
        logger.info(f"ASR 识别成功，文本长度: {len(text)}")
        
        return BaseResponse(
            code=200,
            msg="success",
            data={"text": text}
        )
        
    except httpx.HTTPStatusError as e:
        error_msg = f"ASR API 调用失败: {e.response.status_code}"
        try:
            error_detail = e.response.json()
            error_msg += f" - {error_detail}"
        except:
            error_msg += f" - {e.response.text}"
        logger.error(error_msg)
        return BaseResponse(code=e.response.status_code, msg=error_msg)
    except Exception as e:
        logger.exception(f"ASR 转录出错: {e}")
        return BaseResponse(code=500, msg=f"ASR 转录出错: {str(e)}")


@asr_tts_router.post("/tts/synthesize", summary="文本转语音（TTS）")
async def tts_synthesize(
    request: TTSRequest,
):
    """
    调用硅基流动 TTS 模型，将文本转为语音
    
    返回音频流（audio/wav 或 audio/mpeg）
    
    Args:
        request: TTS 请求参数，包含文本、模型名称、语音类型和速度
        
    Returns:
        StreamingResponse: 音频流响应
    """
    # #region agent log
    import json as json_module
    try:
        with open(r'd:\projects\Langchain-Chatchat\.cursor\debug.log', 'a', encoding='utf-8') as f:
            f.write(json_module.dumps({"sessionId":"debug-session","runId":"run2","hypothesisId":"F","location":"asr_tts_routes.py:118","message":"TTS synthesize endpoint called","data":{"text_length":len(request.text),"model":request.model,"voice":request.voice,"text_preview":request.text[:50]},"timestamp":__import__('time').time()*1000})+'\n')
    except: pass
    # #endregion
    try:
        # 获取模型配置信息
        model_info = get_model_info(model_name=request.model, platform_name="siliconflow")
        if not model_info:
            logger.error(f"未找到 TTS 模型配置: {request.model}")
            return BaseResponse(code=404, msg=f"未找到 TTS 模型 {request.model}")
        
        api_base_url = model_info.get("api_base_url")
        api_key = model_info.get("api_key")
        
        logger.info(f"正在调用 TTS 模型: {request.model}, 文本长度: {len(request.text)}")
        
        # 转换 voice 参数：如果是 OpenAI 标准格式，转换为 SiliconFlow 格式
        voice_param = request.voice
        if ":" not in voice_param:
            # OpenAI 标准格式（如 "alloy"），需要转换为 SiliconFlow 格式
            siliconflow_voice = OPENAI_TO_SILICONFLOW_VOICE.get(voice_param.lower(), "alex")
            voice_param = f"{request.model}:{siliconflow_voice}"
            logger.info(f"转换 voice 参数: '{request.voice}' -> '{voice_param}'")
        
        # 调用硅基流动的 TTS 接口（OpenAI 兼容）
        # 接口路径：/v1/audio/speech
        url = f"{api_base_url}/audio/speech"
        
        payload = {
            "model": request.model,
            "input": request.text,
            "voice": voice_param,  # 格式：FunAudioLLM/CosyVoice2-0.5B:alex
            "speed": request.speed,  # 0.25 - 4.0
            "response_format": request.response_format,  # mp3, opus, wav, pcm
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            # 硅基流动返回音频流
            audio_content = response.content
            content_type = response.headers.get("Content-Type", "audio/mpeg")
        
        logger.info(f"TTS 生成成功，音频大小: {len(audio_content)} bytes")
        
        # #region agent log
        import json as json_module
        try:
            with open(r'd:\projects\Langchain-Chatchat\.cursor\debug.log', 'a', encoding='utf-8') as f:
                f.write(json_module.dumps({"sessionId":"debug-session","runId":"run2","hypothesisId":"G","location":"asr_tts_routes.py:188","message":"TTS audio generated successfully","data":{"audio_size":len(audio_content),"content_type":content_type,"first_bytes":list(audio_content[:20]) if len(audio_content) > 0 else [],"response_headers":dict(response.headers)},"timestamp":__import__('time').time()*1000})+'\n')
        except: pass
        # #endregion
        
        # 返回音频流
        streaming_response = StreamingResponse(
            iter([audio_content]),
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename=speech.mp3"
            }
        )
        
        # #region agent log
        try:
            with open(r'd:\projects\Langchain-Chatchat\.cursor\debug.log', 'a', encoding='utf-8') as f:
                f.write(json_module.dumps({"sessionId":"debug-session","runId":"run2","hypothesisId":"H","location":"asr_tts_routes.py:206","message":"Returning StreamingResponse","data":{"media_type":content_type,"audio_size":len(audio_content),"response_type":"StreamingResponse"},"timestamp":__import__('time').time()*1000})+'\n')
        except: pass
        # #endregion
        
        return streaming_response
        
    except httpx.HTTPStatusError as e:
        error_msg = f"TTS API 调用失败: {e.response.status_code}"
        error_detail = None
        try:
            error_detail = e.response.json()
            error_msg += f" - {error_detail}"
        except:
            error_msg += f" - {e.response.text}"
        logger.error(error_msg)
        # #region agent log
        import json as json_module
        try:
            with open(r'd:\projects\Langchain-Chatchat\.cursor\debug.log', 'a', encoding='utf-8') as f:
                f.write(json_module.dumps({"sessionId":"debug-session","runId":"run2","hypothesisId":"I","location":"asr_tts_routes.py:221","message":"HTTPStatusError - returning BaseResponse","data":{"status_code":e.response.status_code,"error_detail":str(error_detail),"response_type":"BaseResponse"},"timestamp":__import__('time').time()*1000})+'\n')
        except: pass
        # #endregion
        return BaseResponse(code=e.response.status_code, msg=error_msg)
    except Exception as e:
        logger.exception(f"TTS 合成出错: {e}")
        # #region agent log
        import json as json_module
        try:
            with open(r'd:\projects\Langchain-Chatchat\.cursor\debug.log', 'a', encoding='utf-8') as f:
                f.write(json_module.dumps({"sessionId":"debug-session","runId":"run2","hypothesisId":"J","location":"asr_tts_routes.py:233","message":"Generic Exception - returning BaseResponse","data":{"exception_type":type(e).__name__,"exception_msg":str(e),"response_type":"BaseResponse"},"timestamp":__import__('time').time()*1000})+'\n')
        except: pass
        # #endregion
        return BaseResponse(code=500, msg=f"TTS 合成出错: {str(e)}")
