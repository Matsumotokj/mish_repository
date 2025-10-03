from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from .apiapp import get_gemini_response # 作成したサービスをインポート


class AskGeminiView(View):
    def get(self, request):
        # 最初のページ表示
        return render(request, 'apiapp/ask_gemini.html')

    def post(self, request):
        # フォームから送信された質問を取得
        content = request.POST.get('prompt', '')
        length_str = request.POST.get('length', '300')
        info = request.POST.get('info', '')

        speaking_rate = request.POST.get('speed', '1.0')

        playback_mode = request.POST.get('playback_mode', 'auto')


        try:
            length = int(length_str)
        except (ValueError, TypeError):
            length = 300 # 変換に失敗した場合はデフォルト値の300を設定
        
        # Gemini APIから応答を取得
        # gemini_answer = get_gemini_response(
        #     content=content,
        #     length_request=length,
        #     info=info
        # )

        
        # gemini_answer = "この文を入力してください。きっちょう"

        # gemini_answer = f'''皆様、日々の生活で「もっとこうだったら良いのに」と感じる瞬間はありませんか？そのお悩みを、この新商品「スマートアシスト」が解決します。これ一つで、あなたの日常がもっと快適で豊かに。ぜひ、この感動を体験してください。'''

        gemini_answer = "文章1だよ。文章2だよ。"

        # ★★★ 取得した答えをセッションに保存 ★★★
        request.session['correct_answer'] = gemini_answer
        request.session['user_prompt'] = f"「{content}」という内容で、約{length}文字の文章"

        request.session['user_prompt_content'] = content
        request.session['user_prompt_length'] = length
        request.session['user_prompt_info'] = info

        request.session['speaking_rate'] = speaking_rate

        # ★★★ 再生モードもセッションに保存 ★★★
        request.session['playback_mode'] = playback_mode

        return redirect('typeApp:practice')


ask_gemini = AskGeminiView.as_view()

