import {IllustratedHelp} from './Help.tsx';
import React,{useEffect,useRef,useState} from 'react';
import {createRoot} from 'react-dom/client';
import {TopicBubbles} from './TopicBubbles.tsx';
import {NewsDetail,NewsSources} from './NewsDetail.tsx';
import {AttentionGuide} from './Attention.tsx';
import {arr,discussionMarkdown,safeExternalUrl,text,time,updatedTime} from './helpers.ts';
import type {Data} from './helpers.ts';
import './style.css';
import './local.css';

async function request(url:string,body?:Data){
 const response=await fetch(url,{cache:'no-store',...(body?{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{})});
 const value=await response.json();if(!response.ok)throw Error(value.error||'読込に失敗しました。');return value;
}

function Settings({state,onSaved}:{state:Data;onSaved:()=>void}){
 const [draft,setDraft]=useState(()=>structuredClone(state.settings));
 const [revision,setRevision]=useState(state.revision);
 const [tab,setTab]=useState('fields');
 const [busy,setBusy]=useState(false),[notice,setNotice]=useState('');
 const [siteName,setSiteName]=useState(''),[siteUrl,setSiteUrl]=useState('');
 const edit=(index:number,key:string,value:unknown)=>setDraft({...draft,fields:draft.fields.map((field:Data,i:number)=>i===index?{...field,[key]:value}:field)});
 async function save(){setBusy(true);setNotice('');try{const next=await request('/api/settings',{revision,settings:draft});setDraft(next.settings);setRevision(next.revision);setNotice('設定を保存しました。');onSaved()}catch(error){setNotice(String((error as Error).message))}finally{setBusy(false)}}
 return <section className="settingsPage"><h1>設定</h1>
  <p>収集方針の変更後はニュース調査Skillを実行してください。表示設定は保存後に反映します。</p>
  <div className="settingsTabs" role="tablist" aria-label="設定">
   {[['fields','収集分野'],['sites','注目サイト'],['display','表示']].map(([id,label])=><button key={id} role="tab" aria-selected={tab===id} onClick={()=>setTab(id)}>{label}</button>)}
  </div>
  <form onSubmit={event=>{event.preventDefault();save()}}>
  {tab==='fields'&&<div><h2>収集分野</h2><ul className="siteList fieldList">{draft.fields.map((field:Data,index:number)=><li key={field.fieldId} className="card">
   <label>分野名<input required maxLength={100} value={field.name} onChange={event=>edit(index,'name',event.target.value)}/></label>
   <label>どんな情報を集めるか<textarea aria-label="どんな情報を集めるか" required maxLength={4000} rows={4} value={field.instructions} onChange={event=>edit(index,'instructions',event.target.value)}/></label>
   <label><input type="checkbox" checked={field.active} onChange={event=>edit(index,'active',event.target.checked)}/>収集する</label>
   <button type="button" disabled={busy||draft.fields.length===1} onClick={()=>setDraft({...draft,fields:draft.fields.filter((_:Data,i:number)=>i!==index)})}>削除</button>
  </li>)}</ul><button type="button" className="addCard" disabled={busy||draft.fields.length>=50} onClick={()=>setDraft({...draft,fields:[...draft.fields,{fieldId:crypto.randomUUID(),name:'',instructions:'',active:true}]})}>分野を追加</button></div>}
  {tab==='sites'&&<div><h2>注目サイト</h2><p>登録サイトの記事は言語を問わず調査します。</p>
   <ul className="siteList trackedSites">{draft.sites.filter((s:Data)=>s.active).map((site:Data)=><li className="card" key={site.siteId}><div><b>{site.name}</b><a href={safeExternalUrl(site.url)} target="_blank" rel="noopener noreferrer">{site.url}</a></div><button type="button" onClick={()=>setDraft({...draft,sites:draft.sites.map((s:Data)=>s.siteId===site.siteId?{...s,active:false}:s)})}>解除</button></li>)}</ul>
   <div className="siteForm card"><label>サイト名<input value={siteName} maxLength={100} onChange={event=>setSiteName(event.target.value)}/></label><label>URL<input type="url" value={siteUrl} onChange={event=>setSiteUrl(event.target.value)} placeholder="https://example.com/"/></label>
   <button type="button" disabled={!siteName.trim()||!siteUrl.trim()||!siteUrl.startsWith('https://')} onClick={()=>{setDraft({...draft,sites:[...draft.sites,{siteId:crypto.randomUUID(),name:siteName.trim(),url:siteUrl.trim(),active:true}]});setSiteName('');setSiteUrl('')}}>登録</button></div></div>}
  {tab==='display'&&<div className="displaySettings"><h2>表示</h2>{[['zoomPercent','拡大率','%'],['minTopicsPerField','各分野の最低表示数','件']].map(([key,label,unit])=><label key={key}>{label}<select value={draft.displaySettings[key]} onChange={event=>setDraft({...draft,displaySettings:{...draft.displaySettings,[key]:Number(event.target.value)}})}>{state.news.displayConfig.settingsOptions[key].map((n:number)=><option key={n} value={n}>{n}{unit}</option>)}</select></label>)}<p>各分野の上位を指定件数まで表示し、それ以降は話題度が25を超えたものを追加します。</p></div>}
  <div className="settingsActions"><button className="primary" disabled={busy}>設定を保存</button><button type="button" disabled={busy} onClick={()=>{setDraft(structuredClone(state.settings));setRevision(state.revision);setNotice('最新の保存済み設定を読み込みました。')}}>保存済み設定を再読込</button></div>
  </form>{notice&&<p role="status">{notice}</p>}
 </section>;
}

function Information({news}:{news:Data}){
 if(['7','8','9'].includes(news.scoringConfig?.scoreVersion))return <section className="newsInformation"><h2>情報の集め方</h2><ol className="collectionSteps"><li>設定した分野の検索語でGoogleニュースRSSを検索。</li><li>注目サイトはサイト指定でも検索し、記事の本文・日時・出典を確認。</li><li>採点対象の公開指標を取得し、同じ出来事か照合。対象と配点は下の計算式に示します。</li></ol><p>通常記事は日本語、注目サイトは言語不問。登録サイトの全記事を巡回する方式ではありません。24時間／7日間は記事の公開日時で選びます。新しく公開された検証・解説記事も対象です。</p>
 <div className="collectionSites">{arr(news.collectionSites).map(site=><a key={site.siteId} href={safeExternalUrl(site.url)} target="_blank" rel="noopener noreferrer">{site.name}</a>)}</div>
 <AttentionGuide config={news.scoringConfig} collection={news.attentionCollection}/>
 <dl><dt>調査基準時刻</dt><dd>{time(news.referenceAt)}</dd><dt>生成完了</dt><dd>{time(news.generatedAt)}</dd><dt>表示件数</dt><dd>{news.topics.length}件</dd></dl>
 {news.limitations?.length>0&&<><h2>今回の調査の制約</h2><ul>{news.limitations.map((s:string,i:number)=><li key={i}>{s}</li>)}</ul></>}
 </section>;
 return <section className="newsInformation"><h2>情報の集め方</h2><ol className="collectionSteps"><li>設定した収集分野に沿って、GoogleニュースRSSと公開記事を調査します。</li><li>記事本文・公開日時・原典を確認し、同じ出来事と転載を整理します。</li><li>はてなブックマークの現在累計と、独立した報道元の数・伸びから話題度を計算します。</li></ol>
 <p>通常記事は日本語、注目サイトは言語不問。登録サイトの全記事を巡回する方式ではありません。</p>
 <div className="collectionSites">{arr(news.collectionSites).map(site=><a key={site.siteId} href={safeExternalUrl(site.url)} target="_blank" rel="noopener noreferrer">{site.name}</a>)}</div>
 <h2>話題度の計算式</h2><p>話題度 = 100 ×（報道 × 0.7 + 反応 × 0.1 + 伸び × 0.1）</p>
 <dl><dt>報道</dt><dd>min（log（1 + 独立報道元数）÷ log（21）, 1）</dd><dt>反応</dt><dd>min（log（1 + 記事ごとのはてブ累計の最大値）÷ log（501）, 1）</dd><dt>伸び</dt><dd>前の72時間との独立報道元数の比率をlog（比率）÷ log（4）で0〜1へ換算。現在5媒体未満は0。前期0媒体・未調査は欠測。</dd></dl>
 <p>報道は基準時刻から過去72時間を集計します。欠測分を再配分せず、取得しない指標の10％を除いた最高点は90点です。観測充足率70％未満、または独立報道元が2媒体未満の場合は評価不足として扱います。</p>
 <dl><dt>調査基準時刻</dt><dd>{time(news.referenceAt)}</dd><dt>実行</dt><dd>{time(news.executionStartedAt)} 〜 {time(news.executionCompletedAt)}</dd><dt>報道集計</dt><dd>{time(news.reportingWindowStart)} 〜 {time(news.reportingWindowEnd)}</dd><dt>表示件数</dt><dd>{news.topics.length}件</dd><dt>表示対象外</dt><dd>{news.excludedTopicCount}件</dd></dl>
 {news.fieldCoverage.some((f:Data)=>f.shortfall>0)&&<><h2>調査データの不足</h2><ul>{news.fieldCoverage.filter((f:Data)=>f.shortfall>0).map((f:Data)=><li key={f.field}>{f.field}：あと{f.shortfall}件</li>)}</ul></>}
 {news.limitations.length>0&&<><h2>今回の調査の制約</h2><ul>{news.limitations.map((s:string,i:number)=><li key={i}>{s}</li>)}</ul></>}
 </section>;
}

const Help=IllustratedHelp;

function Detail({topic,state,onClose,onKnown,busy}:{topic:Data;state:Data;onClose:()=>void;onKnown:(id:string,known:boolean)=>void;busy:boolean}){
 const dialog=useRef<HTMLElement>(null),[notice,setNotice]=useState('');
 const unknowns=arr(topic.unknowns||topic.unverified||arr(topic.perspectives).filter(entry=>entry.title==='未確認事項'));
 useEffect(()=>{const previous=document.activeElement as HTMLElement;const box=dialog.current!;box.focus();function key(event:KeyboardEvent){if(event.key==='Escape')onClose();if(event.key==='Tab'){const all=[...box.querySelectorAll<HTMLElement>('button:not(:disabled),a[href],input,select,textarea,[tabindex="0"]')];if(!all.length){event.preventDefault();return}const first=all[0],last=all[all.length-1];if(event.shiftKey&&(document.activeElement===first||document.activeElement===box)){last.focus();event.preventDefault()}else if(!event.shiftKey&&(document.activeElement===last||document.activeElement===box)){first.focus();event.preventDefault()}}}document.addEventListener('keydown',key);const overflow=document.body.style.overflow;document.body.style.overflow='hidden';return()=>{document.removeEventListener('keydown',key);document.body.style.overflow=overflow;previous?.focus()}},[]);
 return <div className="overlay" onClick={onClose}><aside className="detail" role="dialog" aria-modal="true" aria-label="ニュース詳細" ref={dialog} tabIndex={-1} onClick={event=>event.stopPropagation()}><button className="close" onClick={onClose}>閉じる</button>
 <NewsDetail topic={topic} knownTermIds={state.preferences.knownTermIds} preferenceReady={true} preferenceBusy={busy} tenants={[]} tenant="local" onTenant={()=>{}} onKnownTerm={onKnown}/>
 <button onClick={async()=>{try{await navigator.clipboard.writeText(discussionMarkdown(topic));setNotice('議論用Markdownをコピーしました。')}catch{setNotice('コピーできませんでした。記事の本文を選択してコピーしてください。')}}}>議論用Markdownをコピー</button>{notice&&<p role="status">{notice}</p>}
 {arr(topic.perspectives).length>0&&<><h3>異なる視点</h3>{arr(topic.perspectives).map((entry,index)=><div className="comparison" key={index}><b>{text(entry.title||entry.viewpoint,'視点')}</b><p>{text(entry.summary||entry.description||entry.text)}</p></div>)}</>}
 {arr(topic.counterHypotheses||topic.hypotheses).length>0&&<><h3>対立仮説</h3>{arr(topic.counterHypotheses||topic.hypotheses).map((entry,index)=><p className="comparison" key={index}>{text(entry.summary||entry.description||entry)}</p>)}</>}
 {unknowns.length>0&&<><h3>未確認事項</h3>{unknowns.map((entry,index)=><p className="comparison" key={index}>{text(entry.summary||entry.description||entry)}</p>)}</>}
 <a className="chatLink" href="https://chatgpt.com/" target="_blank" rel="noopener noreferrer">ChatGPTを開く</a>
 <NewsSources topic={topic}/>
 </aside></div>;
}

function App(){
 const [state,setState]=useState<Data|null>(null),[error,setError]=useState(''),[period,setPeriod]=useState('24h'),[tab,setTab]=useState('chart');
 const [page,setPage]=useState(location.hash.slice(1)||'news'),[selected,setSelected]=useState<Data|null>(null),[busy,setBusy]=useState(false);
 const currentHash=useRef(''),currentPeriod=useRef(period);
 async function refresh(){try{const requested=period;const next=await request('/api/state?period='+requested);if(currentPeriod.current!==requested)return;if(currentHash.current!==next.stateHash){setState(next);currentHash.current=next.stateHash}setError('')}catch(error){setError('データを読み込めません。前回の正常な表示を保持しています。 '+(error as Error).message)}}
 useEffect(()=>{currentPeriod.current=period;let cancelled=false;let timer:ReturnType<typeof setTimeout>;async function loop(){if(cancelled)return;await refresh();if(!cancelled)timer=setTimeout(loop,2000)}loop();return()=>{cancelled=true;clearTimeout(timer)}},[period]);
 useEffect(()=>{const onHash=()=>{setPage(location.hash.slice(1)||'news');setSelected(null)};window.addEventListener('hashchange',onHash);return()=>window.removeEventListener('hashchange',onHash)},[]);
 const news=state?.news;
 const selectedTopic=selected&&(news?.topics.find((t:Data)=>t.topicId===selected.topicId)||selected);
 async function known(id:string,value:boolean){if(!state)return;setBusy(true);try{const ids=new Set<string>(state.preferences.knownTermIds);value?ids.add(id):ids.delete(id);await request('/api/preferences',{knownTermIds:[...ids]});await refresh()}catch(error){setError((error as Error).message)}finally{setBusy(false)}}
 return <><header className="newsToolbar"><a className="brand" href="#news" aria-label="NewsVisualization ホーム"><b>NewsVisualization</b></a>{page==='news'&&<><div className="segments periodButtons" aria-label="対象期間">{[['24h','24時間'],['7d','7日間']].map(([id,label])=><button key={id} className={period===id?'active':''} aria-pressed={period===id} onClick={()=>{setPeriod(id);setSelected(null)}}>{label}</button>)}</div><div className="newsTabs" role="tablist" aria-label="ニュース表示" onKeyDown={event=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){event.preventDefault();const next=event.key==='Home'?'chart':event.key==='End'?'info':tab==='chart'?'info':'chart';setTab(next);document.getElementById(next+'-tab')?.focus()}}}>{[['chart','バブル'],['info','詳細情報']].map(([id,label])=><button id={id+'-tab'} key={id} role="tab" aria-selected={tab===id} tabIndex={tab===id?0:-1} aria-controls={id+'-panel'} onClick={()=>setTab(id)}>{label}</button>)}</div></>}
 <p className="newsUpdatedAt" aria-label="ニュースの更新日時">更新日時：<time dateTime={news?.generatedAt||undefined} title="日本時間">{updatedTime(news?.generatedAt)}</time></p>
 <nav className="headerActions" aria-label="メニュー">{page!=='news'&&<a className="headerLink" href="#news">ニュース</a>}<a className="headerLink" href="#help">使い方</a><a className="headerLink" href="#settings">設定</a></nav></header>
 <main className={page==='news'?'newsMain':'localMain'}>{error&&<p className="error" role="alert">{error}</p>}{!state&&<p role="status">ニュースを読み込んでいます。</p>}
 {page==='news'&&state?.researchStatus?.status==='held'&&<p className="newsStatus researchHeld" role="status">ニュース更新を保留しています。期間内の最低件数に届かないため、前回のニュースを表示しています。<br/>今回の調査：{arr(state.researchStatus.shortfalls).map(item=>`${item.period==='24h'?'24時間':'7日間'}の${item.field}：${item.count}／${item.minimum}件`).join('、')}</p>}
 {page==='help'?<Help/>:state&&page==='settings'?<Settings state={state} onSaved={refresh}/>:news&&<>{news.settingsChanged&&<p className="newsStatus">収集設定が変わりました。次のSkill実行でニュースを更新してください。</p>}{tab==='chart'?<section id="chart-panel" role="tabpanel" aria-labelledby="chart-tab">{news.topics.length===0&&<p className="newsStatus">{news.limitations[0]||'この期間のニュースはありません。'}</p>}<TopicBubbles topics={news.topics} onSelect={setSelected} displayConfig={news.displayConfig} fields={news.displayConfig.fields}/></section>:<section id="info-panel" role="tabpanel" aria-labelledby="info-tab"><Information news={news}/></section>}</>}
 </main>{selectedTopic&&state&&<Detail key={selectedTopic.topicId} topic={selectedTopic} state={state} onClose={()=>setSelected(null)} onKnown={known} busy={busy}/>}</>;
}
createRoot(document.getElementById('root')!).render(<App/>);
