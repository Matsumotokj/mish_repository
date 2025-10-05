from django.shortcuts import render, redirect, get_object_or_404
from django.views import View

from datetime import datetime
from zoneinfo import ZoneInfo
# Create your views here.

from .forms import TranscriptionForm

from apiapp.apiapp import get_gemini_scoring
# from scoring_cmp import grade, to_diff_html, to_diff_ansi

import uuid
import os
from django.conf import settings 

from apiapp.tts import generate_mp3_from_text, split_text_by_punctuation 

import json

from apiapp.tts import generate_mp3_from_text # generate_mp3_from_textをインポート
# from apiapp.apiapp import tts_client # apiapp.pyで初期化されたtts_clientをインポート

class TopView(View):
    def get(self, request):
        date = datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y年%m月%d日 %H:%M:%S")

        return render(request, "typeApp/top.html", {"date": date})
    
top = TopView.as_view()

class PracticeView(View):
    def get(self, request):

        correct_answer = request.session.get("correct_answer", '')
        user_prompt = request.session.get('user_prompt', "")

        speaking_rate = request.session.pop('speaking_rate', "1.0")

        playback_mode = request.session.get('playback_mode', 'auto')

        try:
            speaking_rate = float(speaking_rate)
        except (ValueError, TypeError):
            speaking_rate = 1.0

        # ★★★ ここから句点ごとの処理 ★★★
        phrases = split_text_by_punctuation(correct_answer)
        
        # 音声ファイルパスとテキストのペアを格納するリスト
        audio_data_list = []
        # 削除対象のファイル名（フルパス）を格納するリスト
        # files_to_delete = []

        for i, phrase_text in enumerate(phrases):
            if not phrase_text.strip():
                #空白のみ
                continue
            
            #ユニークな音声ファイル名を作成audio_1とかにpart付けされる
            public_id = f"audio_{uuid.uuid4().hex}_{i}.mp3"
            # audio_filename = f"audio_sample_{i}.mp3"
            # returned_filename = audio_filename

            audio_url = generate_mp3_from_text(phrase_text, public_id, speaking_rate)
            
            if audio_url:
                audio_data_list.append({
                    'id': f'phrase-{i}', # 各フレーズにユニークなIDを付与
                    'text': phrase_text,
                    'audio_url': audio_url
                })
                # 削除のためにファイルのフルパスを保存
                # files_to_delete.append(os.path.join(settings.MEDIA_ROOT, returned_filename))
            else:
                # 音声生成失敗時は、そのフレーズをスキップするか、エラー表示を検討
                print(f"フレーズ '{phrase_text}' の音声生成に失敗しました。")
                # 必要であればエラーハンドリングや、デフォルトのテキスト・音声を追加
                # audio_data_list.append({
                #     'id': f'phrase-{i}',
                #     'text': phrase_text,
                #     'audio_url': os.path.join(settings.MEDIA_URL, "typeApp/audio/error_sound.mp3") # エラー音声の例
                # })

        # ★★★ 生成した音声ファイルのフルパスリストをセッションに保存 ★★★
        # request.session['temp_audio_files_to_delete'] = files_to_delete
        # ★★★ テンプレートに渡すデータも変更 ★★★
        request.session['phrases_data'] = audio_data_list # JSが利用するためにセッションにも保存
        

        form = TranscriptionForm()


        context = {
            # "correct_answer":correct_answer,
            "user_prompt": user_prompt,
            "form": form,
            "phrases_data_json": json.dumps(audio_data_list),
            "playback_mode": playback_mode,
        }

        return render(request, "typeApp/practice.html", context)
    
practice = PracticeView.as_view()



class ResultView(View):
    def post(self, request):

        # user_input = request.POST.get('user-input', '')
        user_input = request.POST.get('text', '')


        # print(user_input)

        # ★★★ 一時的に作成した今回の音声ファイルの削除 (リストで処理) ★★★
        # temp_audio_full_paths = request.session.pop('temp_audio_files_to_delete', []) # popで取得後セッションから削除

        # for file_path in temp_audio_full_paths:
        #     if os.path.exists(file_path):
        #         try:
        #             os.remove(file_path)
        #             print(f"一時音声ファイルを削除しました: {file_path}")
        #         except OSError as e:
        #             print(f"一時音声ファイルの削除に失敗しました {file_path}: {e}")
        #     else:
        #         print(f"警告: 削除対象のファイルが見つかりませんでした: {file_path}")


        # ★★★ セッションから正解データを取得 ★★★
        correct_answer = request.session.get('correct_answer', '')

        print("入力したテキスト：", user_input)


# 後で治す

        # scoring_result = get_gemini_scoring(correct_answer, user_input)

        # context = {
        #     'user_input': user_input,
        #     'correct_answer': correct_answer,
        #     'score': scoring_result.get('score'),
        #     'advice': scoring_result.get('reasons'),
        # }



        context = {
            'user_input': user_input,
            'correct_answer': correct_answer,
            'score': 0,
            'advice': "仮のアドバイス",
        }



        return render(request, "typeApp/result.html", context)
    
result = ResultView.as_view()
