import os
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template

# --- 初期設定 ---
# コードに直接書く代わりに「環境変数」からAPIキーを読み込む
# これにより、APIキーを安全に管理できる
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    # ローカルでテストする際は、一時的にここで設定することも可能
    # ただし、このコードをGitHubなどに公開しないこと
    # api_key = "YOUR_API_KEY_FOR_LOCAL_TEST"
    # 本番環境では環境変数設定が必須
    pass

genai.configure(api_key=api_key)

# (以下、前回のコードと同じ...Flaskアプリケーションの初期化から最後まで)
# ...
app = Flask(__name__)

# プロットデータの読み込み
try:
    with open('Bella.txt', 'r', encoding='utf-8') as f:
        plot_content = f.read()
except FileNotFoundError:
    plot_content = "プロットファイル 'Bella.txt' が見つかりませんでした。"

# Geminiモデルの初期化
# model = genai.GenerativeModel('gemini-pro') # この行は genai.configure の後であれば不要な場合がある

# --- プロンプト（AIへの指示書）を作成する関数 ---
def create_prompt(question, mode, plot):
    """
    ユーザーの選択モードに応じて、Geminiに渡すプロンプトを生成します。
    """
    if mode == 'spoiler-free':
        # ネタバレ無しモードの指示書
        prompt_template = f"""
あなたは漫画『Bella』に関する質問に答える専門家チャットボットです。
以下のルールを厳守して、ユーザーの質問に回答してください。

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
        # ネタバレ有りモードの指示書
        prompt_template = f"""
あなたは漫画『Bella』に関する質問に答える専門家チャットボットです。
以下のルールを厳守して、ユーザーの質問に回答してください。

# ルール
- 提供されたプロット全体の情報を参照して回答してください。
- ただし、32話以降の「未公開の展開」については、直接的な答えを避け、読者の期待を煽るような「におわせる」表現にしてください。
- 例えば、「〇〇という大きな出来事がありますが、それが彼女たちの運命をどう変えるのか、ぜひ本編で確かめてくださいね。」のような形で回答してください。
- 核心的なネタバレは避けつつも、今後の展開への興味を引くようなヒントを少しだけ与えるのがあなたの役割です。

# プロット
{plot}

# ユーザーの質問
{question}
"""
    else:
        return None
    return prompt_template


# --- WebページのルートとAPI ---

# ルートURL ('/') にアクセスがあった場合に index.html を表示
@app.route('/')
def index():
    return render_template('index.html')

# '/ask' へのPOSTリクエストを処理するAPI
@app.route('/ask', methods=['POST'])
def ask_gemini():
    """
    フロントエンドからの質問を受け取り、Geminiに問い合わせて回答を返すAPI。
    """
    data = request.get_json()
    question = data.get('question')
    mode = data.get('mode')  # 'spoiler-free' または 'spoiler-ok'

    if not model:
        return jsonify({"error": "モデルが初期化されていません。APIキーを確認してください。"}), 500
        
    if not question or not mode:
        return jsonify({"error": "質問とモードを指定してください"}), 400

    if plot_content.startswith("プロットファイル"):
        return jsonify({"error": plot_content}), 500

    # プロンプトを作成
    prompt = create_prompt(question, mode, plot_content)
    if not prompt:
        return jsonify({"error": "無効なモードです"}), 400

    try:
        # Geminiにリクエストを送信
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        answer = response.text
        return jsonify({"answer": answer})
    except Exception as e:
        # エラーが発生した場合
        return jsonify({"error": f"Gemini APIとの通信中にエラーが発生しました: {str(e)}"}), 500

# --- アプリケーションの実行 ---
# この部分はRenderがGunicornを使うため、ローカル実行時のみ意味を持つ
if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')