import {useState} from 'react';
import {arr,safeExternalUrl,text,time} from './helpers.ts';
import type {Data} from './helpers.ts';

const statusLabel:Record<string,string>={confirmed:'確認済み',hypothesis:'仮説',unverified:'未確認'};
const applicationLabel:Record<string,string>={work:'仕事',development:'開発',conversation:'会話'};

function SourceCard({source}:{source:Data}){
 const [imageFailed,setImageFailed]=useState(false);
 const link=safeExternalUrl(source.url);
 const thumbnail=safeExternalUrl(source.thumbnailUrl);
 const image=thumbnail.startsWith('https://')&&!imageFailed;
 return <a className="articleCard" href={link} target="_blank" rel="noopener noreferrer">
  {image&&<img src={thumbnail} alt="" loading="lazy" onError={()=>setImageFailed(true)}/>}
  <span className="articleCardText"><small>{text(source.publisherId,link?new URL(link).hostname:'出典')}</small><b>{text(source.title,link)}</b></span>
 </a>;
}

type Props={
 topic:Data;
 knownTermIds:string[];
 preferenceReady:boolean;
 preferenceBusy:boolean;
 tenants:Data[];
 tenant:string;
 onTenant:(tenantId:string)=>void;
 onKnownTerm:(termId:string,known:boolean)=>void;
};
export function NewsDetail({
 topic,knownTermIds,preferenceReady,preferenceBusy,tenants,tenant,onTenant,onKnownTerm,
}:Props){
 const [showKnown,setShowKnown]=useState(false);
 const sources=arr(topic.sources);
 const details=topic.details;
 const cautions=Array.isArray(details?.cautions)?details.cautions:[];
 const terms=arr(details?.terms);
 const hiddenTerms=terms.filter(term=>knownTermIds.includes(term.termId));
 const visibleTerms=terms.filter(term=>showKnown||!knownTermIds.includes(term.termId));
 const reaction=topic.reactionSummary;
 const displayedScore=topic.globalImportanceScore??topic.observedAttentionScore;
 const reactionSource=sources.find(source=>source.sourceId===reaction?.targetSourceId);
 function evidence(entry:Data){
  const linked=arr(entry.supportingSourceIds).map(id=>sources.find(source=>source.sourceId===id&&safeExternalUrl(source.url))).filter((source):source is Data=>!!source);
  return linked.length?<small className="detailEvidence">根拠：{linked.map((source,index)=><span key={source.sourceId}>
   {index>0?'、':''}<a href={safeExternalUrl(source.url)} target="_blank" rel="noopener noreferrer">{text(source.title,source.publisherId)}</a>
  </span>)}</small>:null;
 }
 return <>
  <h2>{text(topic.title||topic.name)}</h2>
  {topic.summary&&<p className="summary">{text(topic.summary)}</p>}
  <div className="metric"><span>話題度</span><strong>
   {displayedScore==null?'—':Number(displayedScore).toFixed(1)}
  </strong></div>
  <p className="reactionDetail">はてブ：{reaction?.count==null?'未取得':`${reaction.count}件`}
   {reaction?.observedAt&&<>（取得：{time(reaction.observedAt)}）</>}
   {reactionSource&&safeExternalUrl(reactionSource.url)&&<>　対象：<a href={safeExternalUrl(reactionSource.url)} target="_blank" rel="noopener noreferrer">{text(reactionSource.title,reactionSource.url)}</a></>}
  </p>
  {details?.explanation&&<section className="detailSection"><h3>記事の要約</h3><p>{details.explanation}</p></section>}
  {cautions.length>0&&<section className="detailSection"><h3>注意ポイント</h3>
   <ul>{cautions.map((caution:string,index:number)=><li key={index}>{caution}</li>)}</ul>
  </section>}
  {terms.length>0&&<section className="detailSection">
   <h3>用語</h3>
   {visibleTerms.map(term=><div className="termEntry" key={term.termId}>
    <b>{term.term}</b><p>{term.description}</p>
    {preferenceReady&&<button disabled={preferenceBusy} onClick={()=>onKnownTerm(term.termId,!knownTermIds.includes(term.termId))}>
     {knownTermIds.includes(term.termId)?'再表示':'知っている'}
    </button>}
   </div>)}
   {hiddenTerms.length>0&&<button className="knownToggle" onClick={()=>setShowKnown(!showKnown)}>
    {showKnown?'既知の用語を隠す':`既知の用語${hiddenTerms.length}件を表示`}
   </button>}
  </section>}
  {arr(details?.background).length>0&&<section className="detailSection"><h3>背景・経緯</h3>
   {arr(details.background).map((entry,index)=><div className="detailItem" key={index}>
    <small>{statusLabel[entry.status]||'未確認'}</small><p>{entry.text}</p>{evidence(entry)}
   </div>)}
  </section>}
  {arr(details?.impacts).length>0&&<section className="detailSection"><h3>世の中への影響</h3>
   {arr(details.impacts).map((entry,index)=><div className="detailItem" key={index}>
    <small>{statusLabel[entry.status]||'未確認'}</small><p>{entry.text}</p>{evidence(entry)}
   </div>)}
  </section>}
  {arr(details?.applications).length>0&&<section className="detailSection"><h3>利用方法</h3>
   {arr(details.applications).map((entry,index)=><div className="detailItem" key={index}>
    <small>{applicationLabel[entry.kind]||text(entry.kind)}</small><p>{entry.text}</p>
   </div>)}
  </section>}
 </>;
}

export function NewsSources({topic}:{topic:Data}){
 const [showAllSources,setShowAllSources]=useState(false);
 const reactionIds=new Set(arr(topic.reactionEvidence).map(item=>item.sourceId));
 const articles=arr(topic.sources).filter(source=>
  safeExternalUrl(source.url)&&!reactionIds.has(source.sourceId)&&!['api','reaction'].includes(source.sourceType)
 );
 const visibleArticles=showAllSources?articles:articles.slice(0,6);
 return articles.length>0?<section className="articleSources" aria-label="出典記事一覧">
   <h3>出典記事一覧</h3>
   <div className="articleGrid">{visibleArticles.map(source=><SourceCard key={source.sourceId} source={source}/>)}</div>
   {articles.length>6&&<button className="articleExpand" onClick={()=>setShowAllSources(!showAllSources)}>
    {showAllSources?'出典を6件に戻す':`ほか${articles.length-6}件の出典を表示`}
   </button>}
  </section>:null;
}
