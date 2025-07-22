import os
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template

# --- 初期設定 ---
# Renderの環境変数からAPIキーを読み込みます
api_key = os.getenv("GOOGLE_API_KEY")

# APIキーが設定されていない場合は、エラーを出してアプリを停止させます
if not api_key:
    raise ValueError("APIキーが設定されていません。Renderの環境変数を確認してください。")

genai.configure(api_key=api_key)

# --- グローバル変数の設定 ---
# AIモデルをアプリ起動時に一度だけ、ここで準備します
try:
    model = genai.GenerativeModel('gemini-pro')
except Exception as e:
    raise RuntimeError(f"Geminiモデルの初期化に失敗しました: {e}")

# プロットファイルを読み込みます
try:
    with open('Bella.txt', 'r', encoding='utf-8') as f:
        plot_content = f.read()
except FileNotFoundError:
    plot_content = "プロットファイル 'Bella.txt' が見つかりませんでした。"

# Flaskアプリケーションを初期化します
app = Flask(__name__)


# --- 関数定義 ---
def create_prompt(question, mode, plot):
    """ユーザーの選択モードに応じて、Geminiに渡すプロンプトを生成します。"""
    if mode == 'spoiler-free':
        prompt_template = f"""
あなたは漫画『Bella』に関する質問に答える専門家チャットボットです。
# ルール
- 参照する情報は、提供されたプロットの「32話まで」に限定してください。
- 33話以降の情報は絶対に回答に含めてはいけません。
- ユーザーが未来の展開について質問しても、「まだ物語で語られていないため、お答えできません。」のように回答してください。
# プロット
{plot}
# ユーザーの質問
{question}
"""
    elif mode == 'spoiler-ok':
        prompt_template = f"""
あなたは漫画『Bella』に関する質問に答える専門家チャットボットです。
# ルール
- 提供されたプロット全体の情報を参照して回答してください。
- ただし、32話以降の「未公開の展開」については、直接的な答えを避け、読者の期待を煽るような「におわせる」表現にしてください。
- 例えば、「〇〇という大きな出来事がありますが、それが彼女たちの運命をどう変えるのか、ぜひ本編で確かめてくださいね。」のような形で回答してください。
# プロット
{plot}
# ユーザーの質問
{question}
"""
    else:
        return None
    return prompt_template

# --- WebページのルートとAPI ---
@app.route('/')
def index():
    """トップページ（index.html）を表示します。"""
    return render_template('index.html')

@app.route('/ask', methods=['POST'])
def ask_gemini():
    """フロントエンドからの質問を受け取り、Geminiに問い合わせて回答を返すAPIです。"""
    data = request.get_json()
    question = data.get('question')
    mode = data.get('mode')

    if not question or not mode:
        return jsonify({"error": "質問とモードを指定してください"}), 400

    if plot_content.startswith("プロットファイル"):
        return jsonify({"error": plot_content}), 500

    prompt = create_prompt(question, mode, plot_content)
    if not prompt:
        return jsonify({"error": "無効なモードです"}), 400

    try:
        # アプリ起動時に準備した「model」変数をここで使います
        response = model.generate_content(prompt)
        answer = response.text
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"error": f"Gemini APIとの通信中にエラーが発生しました: {str(e)}"}), 500

# この部分はローカルでのテスト実行時に使われます
if __name__ == '__main__':
    # Renderはgunicornを使うので、この部分は本番環境では実行されません
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))