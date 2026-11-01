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
