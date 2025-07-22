import os
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template

# --- 初期設定 ---
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("APIキーが設定されていません。Renderの環境変数を確認してください。")
genai.configure(api_key=api_key)

# --- グローバル変数の設定 ---
# AIモデルをアプリ起動時に一度だけ準備します
try:
    model = genai.GenerativeModel('gemini-1.0-pro')
except Exception as e:
    raise RuntimeError(f"Geminiモデルの初期化に失敗しました: {e}")

# 3つのプロットファイルを読み込みます
def load_plot_file(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f"プロットファイル '{filename}' が見つかりませんでした。"

main_plot_content = load_plot_file('bella_main.txt')
sequel_plot_content = load_plot_file('plot.txt')
prequel_plot_content = load_plot_file('Original.txt')

app = Flask(__name__)

# --- 関数定義 ---
def create_prompt(question, mode):
    """ユーザーの選択モードに応じて、Geminiに渡すプロンプトを生成します。"""
    if mode == 'spoiler-free':
        prompt_template = f"""
あなたは漫画『Bella』に関する質問に答える専門家チャットボットです。
# ルール
- 参照する情報は、提供されたメインプロットの「32話まで」に限定してください。
- 33話以降の情報、続編プロット、前日譚プロットの情報は絶対に回答に含めてはいけません。
- ユーザーが未来の展開について質問しても、「現在公開されている範囲では、まだ語られていません。」のように回答してください。

# メインプロット (bella_main.txt)
{main_plot_content}

# ユーザーの質問
{question}
"""
    elif mode == 'spoiler-ok':
        prompt_template = f"""
あなたは漫画『Bella』シリーズに関する質問に答える、知識豊富な解説者です。
# ルール
- 提供された「前日譚」「メインプロット」「続編プロット」の全ての情報を最大限に活用し、ユーザーの質問に回答してください。
- あなたの役割は、物語の全貌を理解しているファンからの深い質問に答えることです。
- 情報を隠したり、におわせたりせず、「徹底的に」「詳しく」解説してください。
- 物語の時系列（前日譚→メイン→続編）を意識し、キャラクターの動機や出来事の背景などを深く掘り下げて説明してください。

# 前日譚プロット (Original.txt)
{prequel_plot_content}
---
# メインプロット (bella_main.txt)
{main_plot_content}
---
# 続編プロット (plot.txt)
{sequel_plot_content}
---
# ユーザーの質問
{question}
"""
    else:
        return None
    return prompt_template

# --- WebページのルートとAPI ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ask', methods=['POST'])
def ask_gemini():
    # ファイル読み込みエラーがないかチェック
    for content in [main_plot_content, sequel_plot_content, prequel_plot_content]:
        if "見つかりませんでした" in content:
            return jsonify({"error": content}), 500
            
    data = request.get_json()
    question = data.get('question')
    mode = data.get('mode')

    if not question or not mode:
        return jsonify({"error": "質問とモードを指定してください"}), 400

    prompt = create_prompt(question, mode)
    if not prompt:
        return jsonify({"error": "無効なモードです"}), 400

    try:
        response = model.generate_content(prompt)
        # Markdown形式の回答を適切に処理
        answer = response.text
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"error": f"Gemini APIとの通信中にエラーが発生しました: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))