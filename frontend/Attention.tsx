import {time} from './helpers.ts';
import type {Data} from './helpers.ts';
import {Formula} from './Formula.tsx';

const labels:Record<string,string>={reporting:'独立報道元',reaction:'はてなブックマーク',growth:'報道の伸び',google:'Googleトレンド',wikipedia:'Wikipedia閲覧増',yahoo:'Yahoo!ニュース順位',livedoor:'ライブドア順位',gdelt:'GDELT報道シェア'};

export function AttentionGuide({config,collection}:{config:Data;collection?:Data}){
 const w=config.weights;
 const symbols:Record<string,string>={reporting:'R',reaction:'H',growth:'G',google:'T',wikipedia:'W',yahoo:'Y',livedoor:'L',gdelt:'D'};
 const active=Object.entries(w).filter(([,weight])=>Number(weight)>0);
 const maximum=Math.round(active.reduce((sum,[,weight])=>sum+Number(weight),0)*100);
 return <section className="scoreCalculation" aria-label="話題度の計算式"><h2>話題度の計算式（現行）</h2><small>logは自然対数、minは小さい方、maxは大きい方、round₁は小数第1位への丸めです。各指標は0〜1へ換算します。採点方式：{config.scoreVersion}。</small>
 <h3>通常ニュースの話題度</h3><small>Sは観測できた分の話題度。欠測の項は合計から除き、重みは配り直しません。最高{maximum}点です。</small>
 <Formula line={`S = round₁(100 × (${active.map(([key,weight])=>`${weight} × ${symbols[key]}`).join(' + ')}))`}/>
 <ul>{active.map(([key,weight])=><li key={key}>{labels[key]||key}：{Number(weight)*100}点</li>)}</ul>
 {w.wikipedia===0&&w.gdelt===0&&<p>WikipediaとGDELTは収集・採点の対象外です。{config.scoreVersion==='8'?'除外した15点をほかの指標へ再配分していません。':''}</p>}
 {config.scoreVersion==='9'&&<p>検索・ランキングの代替枠は合計{Math.round((w.google+w.yahoo+w.livedoor)*100)}点です。Googleトレンド{w.google*100}点、Yahoo!ニュース{w.yahoo*100}点、ライブドア{w.livedoor*100}点として加算します。検索・閲覧順位は投稿件数と異なる指標です。固定の加算点はありません。</p>}
 <h3>独立報道元 R</h3><small>Pは過去{config.reportingHours}時間の独立原典媒体数。転載は原典へまとめます。{config.publisherBaseline}媒体で上限です。</small>
 <Formula line={`R = min(log(1 + P) / log(1 + ${config.publisherBaseline}), 1)`}/>
 <h3>はてなブックマーク H</h3><small>Bは記事ごとの現在累計の最大値。期間内の増分ではありません。</small>
 <Formula line={`H = min(log(1 + B) / log(1 + ${config.reactionCountBaseline}), 1)`}/>
 <h3>報道の伸び G</h3><small>P前期はその前の{config.reportingHours}時間の独立原典媒体数。前期が0又は未調査なら欠測です。前期が確認済みで1以上のとき、現在{config.growthMinPublishers}媒体未満は0、それ以外は次の式です。</small>
 <Formula line={`G = min(max(log(P / P前期) / log(${config.growthFullRatio}), 0), 1)`}/>
 <h3>Googleトレンド T</h3><small>Qは日本向け急上昇RSSの概算検索数の下限。同じ出来事の複数行は最大値。{config.googleTrafficBaseline.toLocaleString()}検索で上限です。</small>
 <Formula line={`T = min(log(1 + Q) / log(1 + ${config.googleTrafficBaseline}), 1)`}/>
 <small>RSS非掲載は検索数0を意味しないため欠測です。取得時点の値であり、72時間の総検索数ではありません。</small>
 {w.wikipedia>0&&<><h3>Wikipedia閲覧増 W</h3><small>Vは出来事固有の日本語ページの完了UTC日のuser閲覧数、Mはその前28日の中央値。連続29日分が必要です。Vが0ならWは0、それ以外は次の式です。</small>
 <Formula line={`W = min(max(log(V / max(M, ${config.wikipediaBaselineFloor})) / log(${config.wikipediaFullRatio}), 0), 1)`}/></>}
 <h3>Yahoo!ニュース順位 Y・ライブドア順位 L</h3><small>rは取得時点の総合順位、Nは取得した完全な一覧の件数。各提供者で別々に計算します。</small>
 <Formula line="Y = (N - r + 1) / N"/><Formula line="L = (N - r + 1) / N"/>
 <small>1位は1、最下位は1／Nです。全一覧を照合して圏外と確認できた場合だけ0、取得・照合失敗は欠測です。</small>
 {w.gdelt>0&&<><h3>GDELT報道シェア D</h3><small>Aは過去{config.reportingHours}時間の出来事に一致する記事数、Zは同期間の収録総件数。全世界の全記事の件数ではありません。分母が取得できなければ欠測です。</small>
 <Formula line={`D = min((A / Z) / ${config.gdeltFullShare}, 1)`}/></>}
 <p>独立原典{config.minIndependentPublishers}媒体未満、又は観測済み配点が{Math.round(config.minDataCompleteness*10000)/100}{maximum<100?'点':'％'}未満の場合は評価不足として、観測できた分の点数を表示します。ニュースの重要性や世論の支持率ではありません。</p>
 {collection&&<><h2>今回の公開指標の収集</h2><ul>{['google','yahoo','livedoor'].map(key=>{const item=collection[key];return item&&<li key={key}>{labels[key]}：{item.status==='available'?`一覧${item.itemCount}件を取得`:'取得できず'}（{time(item.observedAt)}）{item.error&&` ${item.error}`}</li>})}</ul><p>一覧を取得できたことと、各ニュースに対応する値を得たことは別です。</p></>}
 </section>;
}
