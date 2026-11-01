export type Data = Record<string, any>;
export const text=(value:any,fallback='不明')=>typeof value==='string'&&value?value:typeof value==='number'?String(value):fallback;
export const arr=(value:unknown):Data[]=>Array.isArray(value)?value:[];
export function updatedTime(value:unknown):string{
 if(typeof value!=='string'||!value)return '未更新';
 const date=new Date(value);
 if(isNaN(+date))return '未更新';
 const parts=new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(date);
 const get=(type:string)=>parts.find(part=>part.type===type)?.value;
 return `${get('year')}-${get('month')}-${get('day')} ${get('hour')}:${get('minute')}`;
}
export const time=(value:any)=>{
 if(!value)return '不明';
 if(typeof value==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(value))return value.replace(/-/g,'/')+'（時刻不明）';
 const date=new Date(value);
 return isNaN(+date)?text(value):new Intl.DateTimeFormat('ja-JP',{timeZone:'Asia/Tokyo',dateStyle:'medium',timeStyle:'short'}).format(date)+' JST';
};
const str=(v:unknown,f='')=>typeof v==='string'&&v?v:f;
export function safeExternalUrl(value:unknown):string{try{const u=new URL(str(value));return u.protocol==='https:'||u.protocol==='http:'?u.href:''}catch{return ''}}
export function bubbleDiameter(score:unknown,minRadius:number,maxRadius:number,exponent=1):number{
 if(!Number.isFinite(minRadius)||!Number.isFinite(maxRadius)||minRadius<=0||maxRadius<minRadius||!Number.isFinite(exponent)||exponent<1||exponent>4)throw Error('Invalid bubble radius');
 const n=typeof score==='number'&&Number.isFinite(score)?Math.max(0,Math.min(100,score)):0;
 return 2*Math.sqrt(minRadius*minRadius+(n/100)**exponent*(maxRadius*maxRadius-minRadius*minRadius));
}
export function discussionMarkdown(item:Data):string{
 const sources=arr(item.sources).map(source=>{const url=safeExternalUrl(source.url);return url?'- '+str(source.title,url)+': '+url:''}).filter(Boolean);
 const views=arr(item.perspectives).map(view=>'- '+str(view.title||view.viewpoint,'視点')+': '+str(view.summary||view.description,'未確認'));
 const hypotheses=arr(item.counterHypotheses||item.hypotheses).map(entry=>'- '+str(entry.summary||entry.description||entry,'未確認'));
 const unknowns=arr(item.unknowns||item.unverified).map(entry=>'- '+str(entry.summary||entry.description||entry,'不明'));
 return ['# '+str(item.title,'ニュース'),'## 要約',str(item.summary,'不明'),'## 事実と根拠',str(item.facts,'未確認'),
  '## 異なる視点',...views,'## 対立仮説',...hypotheses,'## 未確認事項',...unknowns,
  '## 検討論点','- この変化は誰にどのような影響を与えるか。','## 出典',...sources].join('\n');
}
