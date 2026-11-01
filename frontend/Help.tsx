import React from 'react';
import './help.css';

function FlowIllustration(){return <svg className="helpFlowWide" viewBox="0 0 960 290" role="img" aria-label="Codexへニュース更新を依頼し、収集・確認・採点を経てJSONを上書きすると、画面に自動反映する流れ">
 <rect x="1" y="1" width="958" height="288" rx="22" fill="#f7faff"/>
 <path d="M270 143H346M326 127l20 16-20 16M613 143h76M669 127l20 16-20 16" fill="none" stroke="#9aa8b9" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/>
 <rect x="35" y="63" width="235" height="151" rx="14" fill="white" stroke="#bcd1f5" strokeWidth="2"/>
 <rect x="35" y="63" width="235" height="33" rx="14" fill="#e8f0fe"/>
 <text x="57" y="85" fill="#185abc" fontSize="15" fontWeight="700">1　Codexへ依頼</text>
 <rect x="54" y="113" width="196" height="64" rx="12" fill="#4285f4"/>
 <path d="M224 177v14l-18-14" fill="#4285f4"/>
 <text x="69" y="138" fill="white" fontSize="14">ニュースを更新して</text>
 <text x="69" y="159" fill="white" fontSize="11">nv-news-researchを実行</text>
 <rect x="357" y="47" width="245" height="188" rx="14" fill="white" stroke="#bfdcc9" strokeWidth="2"/>
 <text x="379" y="77" fill="#188038" fontSize="15" fontWeight="700">2　収集・確認・採点</text>
 <rect x="376" y="93" width="65" height="91" rx="5" fill="#e6f4ea"/><rect x="449" y="93" width="65" height="91" rx="5" fill="#fef7e0"/><rect x="522" y="93" width="61" height="91" rx="5" fill="#e8f0fe"/>
 <path d="M386 116h44m-44 12h36m-36 12h40m-40 12h29M460 116h43m-43 12h32m-32 12h40m-40 12h26" stroke="#9daeb0" strokeWidth="3" strokeLinecap="round"/>
 <text x="537" y="125" fill="#185abc" fontSize="17" fontWeight="700">JSON</text><text x="537" y="150" fill="#185abc" fontSize="23">{'{ }'}</text>
 <text x="377" y="209" fill="#53606d" fontSize="13">正常な結果だけを上書き保存</text>
 <rect x="700" y="63" width="226" height="151" rx="13" fill="white" stroke="#bcd1f5" strokeWidth="2"/>
 <path d="M700 95h226" stroke="#dbe3ee"/><text x="716" y="84" fill="#185abc" fontSize="14" fontWeight="700">3　画面に反映</text>
 <circle cx="750" cy="143" r="30" fill="#4285f4"/><circle cx="800" cy="159" r="18" fill="#34a853"/><circle cx="850" cy="139" r="24" fill="#ea4335"/><circle cx="883" cy="170" r="13" fill="#fbbc05"/>
 <text x="714" y="259" fill="#53606d" fontSize="13">表示中なら約2秒で更新</text>
</svg>}

function FlowStackIllustration(){return <svg className="helpFlowTall" viewBox="0 0 360 650" role="img" aria-label="Codexへの依頼、記事の収集とJSON保存、画面への反映を上から順に示す図">
 <rect x="1" y="1" width="358" height="648" rx="18" fill="#f7faff"/>
 <rect x="30" y="25" width="300" height="155" rx="13" fill="white" stroke="#bcd1f5" strokeWidth="2"/>
 <text x="49" y="55" fill="#185abc" fontSize="17" fontWeight="700">1　Codexへ依頼</text>
 <rect x="49" y="75" width="261" height="73" rx="12" fill="#4285f4"/><text x="66" y="105" fill="white" fontSize="16">ニュースを更新して</text><text x="66" y="128" fill="white" fontSize="12">nv-news-researchを実行</text>
 <path d="M180 191v29m-10-10 10 10 10-10M180 409v29m-10-10 10 10 10-10" fill="none" stroke="#9aa8b9" strokeWidth="3" strokeLinecap="round"/>
 <rect x="30" y="232" width="300" height="165" rx="13" fill="white" stroke="#bfdcc9" strokeWidth="2"/>
 <text x="49" y="264" fill="#188038" fontSize="17" fontWeight="700">2　収集・確認・採点</text>
 <rect x="50" y="284" width="66" height="83" rx="6" fill="#e6f4ea"/><rect x="125" y="284" width="66" height="83" rx="6" fill="#fef7e0"/><rect x="203" y="284" width="104" height="83" rx="6" fill="#e8f0fe"/>
 <path d="M61 304h43m-43 13h33m-33 13h40M137 304h42m-42 13h32m-32 13h38" stroke="#9daeb0" strokeWidth="3" strokeLinecap="round"/>
 <text x="219" y="316" fill="#185abc" fontSize="18" fontWeight="700">JSON</text><text x="236" y="348" fill="#185abc" fontSize="26">{'{ }'}</text>
 <rect x="30" y="450" width="300" height="169" rx="13" fill="white" stroke="#bcd1f5" strokeWidth="2"/>
 <text x="49" y="482" fill="#185abc" fontSize="17" fontWeight="700">3　画面へ自動反映</text><circle cx="92" cy="546" r="34" fill="#4285f4"/><circle cx="164" cy="552" r="23" fill="#34a853"/><circle cx="227" cy="540" r="30" fill="#ea4335"/><circle cx="282" cy="562" r="16" fill="#fbbc05"/>
 <text x="49" y="603" fill="#53606d" fontSize="13">正常な結果を保存すると約2秒で反映</text>
</svg>}

function BubblesIllustration(){return <svg viewBox="0 0 620 360" role="img" aria-label="24時間と7日間を切り替え、分野の色とバブルの大きさで話題を見つける画面例">
 <rect x="12" y="14" width="596" height="332" rx="16" fill="white" stroke="#d8e1ec" strokeWidth="2"/>
 <rect x="12" y="14" width="596" height="48" rx="16" fill="#f6f8fc"/>
 <rect x="33" y="25" width="73" height="28" rx="7" fill="#4285f4"/><text x="44" y="44" fill="white" fontSize="14">24時間</text><text x="120" y="44" fill="#53606d" fontSize="14">7日間</text>
 <text x="34" y="89" fill="#4285f4" fontSize="14" fontWeight="700">AI・技術</text><text x="341" y="89" fill="#188038" fontSize="14" fontWeight="700">セキュリティ</text>
 <circle cx="125" cy="178" r="62" fill="#4285f4"/><circle cx="232" cy="146" r="32" fill="#4285f4"/><circle cx="222" cy="229" r="42" fill="#4285f4"/>
 <text x="125" y="172" textAnchor="middle" fill="white" fontSize="15">話題の見出し</text><text x="125" y="197" textAnchor="middle" fill="white" fontSize="20">48</text>
 <circle cx="400" cy="157" r="44" fill="#34a853"/><circle cx="503" cy="209" r="59" fill="#34a853"/><circle cx="400" cy="252" r="29" fill="#34a853"/>
 <text x="503" y="204" textAnchor="middle" fill="white" fontSize="15">選んで詳細へ</text><text x="503" y="229" textAnchor="middle" fill="white" fontSize="20">36</text>
 <rect x="76" y="297" width="60" height="27" rx="7" fill="#f7faff" stroke="#d8e1ec"/><text x="88" y="316" fill="#4285f4" fontSize="12">前へ</text><text x="151" y="316" fill="#53606d" fontSize="12">1 / 2</text><rect x="191" y="297" width="60" height="27" rx="7" fill="#f7faff" stroke="#d8e1ec"/><text x="203" y="316" fill="#4285f4" fontSize="12">次へ</text>
</svg>}

function DetailIllustration(){return <svg viewBox="0 0 620 360" role="img" aria-label="選んだニュースの詳細で、話題度、記事の要約、用語、根拠となる出典を確認する例">
 <rect x="12" y="14" width="596" height="332" rx="16" fill="#f7faff" stroke="#d8e1ec" strokeWidth="2"/>
 <circle cx="100" cy="122" r="54" fill="#4285f4" opacity=".17"/><circle cx="181" cy="223" r="38" fill="#34a853" opacity=".17"/>
 <rect x="247" y="14" width="361" height="332" rx="14" fill="white"/><path d="M247 15v330" stroke="#4285f4" strokeWidth="2"/>
 <text x="271" y="52" fill="#202124" fontSize="18" fontWeight="700">ニュースの見出し</text><text x="540" y="48" fill="#53606d" fontSize="12">閉じる</text>
 <rect x="271" y="70" width="311" height="44" rx="7" fill="#e8f0fe"/><text x="285" y="98" fill="#185abc" fontSize="13">話題度</text><text x="544" y="99" fill="#185abc" fontSize="21" fontWeight="700">48.2</text>
 <text x="271" y="141" fill="#202124" fontSize="14" fontWeight="700">記事の要約</text><path d="M272 157h294m-294 12h264" stroke="#c7d2df" strokeWidth="5" strokeLinecap="round"/>
 <text x="271" y="202" fill="#202124" fontSize="14" fontWeight="700">用語</text><text x="271" y="224" fill="#53606d" fontSize="12">必要な言葉を、短い説明で確認</text>
 <rect x="462" y="190" width="120" height="29" rx="7" fill="white" stroke="#a8c7fa"/><text x="480" y="210" fill="#185abc" fontSize="12">知っている</text>
 <text x="271" y="260" fill="#202124" fontSize="14" fontWeight="700">出典記事一覧</text><rect x="271" y="274" width="147" height="47" rx="7" fill="#f6f8fc" stroke="#d8e1ec"/><rect x="432" y="274" width="150" height="47" rx="7" fill="#f6f8fc" stroke="#d8e1ec"/>
 <text x="282" y="302" fill="#53606d" fontSize="12">原典・公式発表</text><text x="444" y="302" fill="#53606d" fontSize="12">報道・解説記事</text>
</svg>}

function SettingsIllustration(){return <svg viewBox="0 0 620 290" role="img" aria-label="設定で収集分野と集めたい情報を書き、注目サイトや拡大率も変更できる例">
 <rect x="12" y="14" width="596" height="262" rx="16" fill="white" stroke="#d8e1ec" strokeWidth="2"/>
 <text x="37" y="48" fill="#202124" fontSize="17" fontWeight="700">設定</text><text x="37" y="81" fill="#185abc" fontSize="14">収集分野</text><text x="143" y="81" fill="#53606d" fontSize="14">注目サイト</text><text x="261" y="81" fill="#53606d" fontSize="14">表示</text><path d="M36 91h78" stroke="#4285f4" strokeWidth="3"/>
 <text x="37" y="122" fill="#53606d" fontSize="12">分野名</text><rect x="37" y="132" width="245" height="35" rx="6" fill="#f7faff" stroke="#c7d2df"/><text x="49" y="155" fill="#202124" fontSize="14">AI・技術</text>
 <text x="37" y="192" fill="#53606d" fontSize="12">どんな情報を集めるか</text><rect x="37" y="202" width="365" height="49" rx="6" fill="#f7faff" stroke="#c7d2df"/><text x="49" y="224" fill="#53606d" fontSize="12">公式発表と検証記事を優先し、</text><text x="49" y="241" fill="#53606d" fontSize="12">提供段階や利用条件も確認する。</text>
 <rect x="441" y="210" width="137" height="40" rx="8" fill="#4285f4"/><text x="468" y="236" fill="white" fontSize="14">設定を保存</text>
</svg>}

export function IllustratedHelp(){return <section className="illustratedHelp">
 <div className="helpIntro"><p className="helpEyebrow">使い方ガイド</p><h1>NewsVisualizationの使い方</h1><p>ニュースを集めて、世の中で何が話題かを確かめる。<br/>更新はCodexへ依頼し、画面で話題と根拠を読みます。</p></div>
 <article className="helpFlow"><h2><span className="helpNumber">1</span>ニュースを更新する</h2><p>このプロジェクトを開いたCodexへ、次のように依頼します。</p><blockquote>nv-news-researchでニュースを更新して</blockquote><figure><FlowIllustration/><FlowStackIllustration/><figcaption>Skillが記事を収集して内容と出典を確認し、Pythonで採点します。正常な結果だけをdata/news.jsonへ上書きし、表示中の画面へ反映します。</figcaption></figure></article>
 <div className="illustratedHelpGrid"><article><h2><span className="helpNumber">2</span>バブルから話題を選ぶ</h2><figure><BubblesIllustration/><figcaption>24時間／7日間を切り替え、期間内に公開された記事の話題を見ます。古い出来事を扱った新しい記事も対象です。バブルを選ぶと詳細が開きます。「前へ」「次へ」で各分野のページを移動できます。</figcaption></figure><p className="helpNote">バブルの大きさは表示中の話題度の相対値です。数値は記事の正しさや、個人への重要度を示すものではありません。</p></article>
 <article><h2><span className="helpNumber">3</span>要約と出典を確かめる</h2><figure><DetailIllustration/><figcaption>概要、記事の要約、背景・影響・利用方法を確認し、出典から原記事へ進めます。「採点の内訳」ではGoogleトレンドなどの実測値・加点・欠測理由を確認できます。用語の「知っている」を押すと、次回からその説明を隠します。</figcaption></figure><p className="helpNote">「既知の用語を表示」で説明を確認し、「再表示」で元に戻せます。閉じるボタンやEscキーで一覧に戻ります。</p></article></div>
 <article className="helpSettings"><div><h2><span className="helpNumber">4</span>集める情報を設定する</h2><p>「設定」で収集分野、収集方針、注目サイト、拡大率、最低表示数を編集します。収集方針は次のSkill実行から、表示設定は保存後に反映します。</p><p className="helpNote">通常の記事は日本語、注目サイトの記事は言語を問わず調査します。</p></div><figure><SettingsIllustration/><figcaption>ファイルの直接編集と、設定画面からの保存は順番に行ってください。</figcaption></figure></article>
 <aside className="helpStorage"><h2>データはローカルに保存します</h2><p>ニュース・設定・既知用語は、サーバー終了後もファイルに残ります。画面は約2秒ごとに更新を確認します。不正なJSONでは前回の正常な画面を保持し、ファイルの修正後に復帰します。</p><p>画面を開くだけでは調査を開始しません。記事の要約や数値は、画面の「調査基準時刻」時点の情報です。</p></aside>
 </section>}
