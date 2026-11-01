import {bubbleDiameter} from './helpers.ts';

export type Topic = {topicId:string;category?:string;field?:string;globalImportanceScore?:number|null;observedAttentionScore?:number|null;sizeScore?:number};
export type DisplayConfig = {zoomPercent?:number;minTopicsPerField:number;pageSize:number;minRadius:number;maxRadius:number;sizeExponent:number;mobileViewportScreens:number;gap:number;parentPadding:number;labelFontRatio:number;labelMinFontSize:number;labelMaxFontSize:number;labelMaxLines:number;additionalThreshold:number;fields:string[];aliases:Record<string,string>};

export function isDisplayConfig(value:unknown):value is DisplayConfig {
  if(!value||typeof value!=='object')return false;
  const c=value as Record<string,unknown>;
  const fields=c.fields;
  const number=(key:string,min:number,max:number)=>typeof c[key]==='number'&&Number.isFinite(c[key])&&(c[key] as number)>=min&&(c[key] as number)<=max;
  return Number.isInteger(c.minTopicsPerField)&&number('minTopicsPerField',1,50)
    &&Number.isInteger(c.pageSize)&&number('pageSize',1,50)&&(c.pageSize as number)>=(c.minTopicsPerField as number)
    &&number('minRadius',1,300)&&number('maxRadius',1,300)&&(c.maxRadius as number)>=(c.minRadius as number)
    &&number('mobileViewportScreens',1,10)&&number('sizeExponent',1,4)&&number('gap',0,100)&&number('parentPadding',0,100)
    &&number('labelFontRatio',.02,.3)&&number('labelMinFontSize',6,32)&&number('labelMaxFontSize',6,96)
    &&(c.labelMinFontSize as number)<=(c.labelMaxFontSize as number)&&Number.isInteger(c.labelMaxLines)&&number('labelMaxLines',1,10)&&number('additionalThreshold',0,100)
    &&Array.isArray(fields)&&fields.every((f:unknown)=>typeof f==='string'&&!!f)
    &&new Set(fields).size===fields.length&&!!c.aliases&&typeof c.aliases==='object'&&!Array.isArray(c.aliases)
    &&Object.entries(c.aliases).every(([key,field])=>!!key&&fields.includes(field));
}

export function groupTopics<T extends Topic>(topics:T[], mapping:Record<string,string>,fields:string[]) {
  const groups = new Map<string,T[]>();
  for (const topic of topics) {
    const category = topic.category || 'その他';
    const mapped = Object.hasOwn(mapping,category) ? mapping[category] : undefined;
    const label = topic.field || (typeof mapped==='string' && mapped.trim() ? mapped : category);
    const members = groups.get(label) || [];
    members.push(topic);
    groups.set(label,members);
  }
  return [...groups].map(([label,members])=>({label,topics:members})).sort((a,b)=>{
    const rank=(label:string)=>fields.includes(label)?fields.indexOf(label):fields.length;
    return rank(a.label)-rank(b.label)||a.label.localeCompare(b.label,'ja');
  });
}

type Circle = {topicId:string;x:number;y:number;radius:number};

// 接する候補を比較し、円の重なりを避けながら縦横に広がり過ぎない位置を選ぶ。
export function packTopics(topics:Topic[],width:number,cfg:DisplayConfig) {
  const {minRadius,maxRadius,gap}=cfg;
  if(!Number.isFinite(width)||width<=0||!Number.isFinite(gap)||gap<0)throw Error('Invalid chart dimensions');
  const padding=cfg.parentPadding;
  const usable=Math.max(1,width-2*padding);
  const circles:Circle[]=[];
  const ordered=topics.map(t=>({topicId:t.topicId,radius:Math.min(bubbleDiameter(t.sizeScore??t.globalImportanceScore??t.observedAttentionScore,minRadius,maxRadius,cfg.sizeExponent)/2,usable/2)}))
    .sort((a,b)=>b.radius-a.radius||a.topicId.localeCompare(b.topicId));
  for(const item of ordered) {
    const r=item.radius;
    const bottom=circles.length?Math.max(...circles.map(c=>c.y+c.radius)):0;
    const candidates=[{x:usable/2,y:bottom+r+(circles.length?gap:0)}];
    for(const other of circles) {
      for(let angle=0;angle<48;angle++) {
        const radians=angle*Math.PI/24;
        candidates.push({x:other.x+(other.radius+r+gap)*Math.cos(radians),y:other.y+(other.radius+r+gap)*Math.sin(radians)});
      }
    }
    // 既配置の2円に同時に接する位置は、角度の近似候補より隙間を詰めやすい。
    for(let i=0;i<circles.length;i++)for(let j=i+1;j<circles.length;j++) {
      const a=circles[i],b=circles[j],dx=b.x-a.x,dy=b.y-a.y,d=Math.hypot(dx,dy);
      const ra=a.radius+r+gap,rb=b.radius+r+gap;
      if(!d||d>ra+rb||d<Math.abs(ra-rb))continue;
      const along=(ra*ra-rb*rb+d*d)/(2*d),h=Math.sqrt(Math.max(0,ra*ra-along*along));
      for(const sign of [-1,1])candidates.push({x:a.x+along*dx/d-sign*h*dy/d,y:a.y+along*dy/d+sign*h*dx/d});
    }
    let best=candidates[0],cost=Infinity;
    for(const position of candidates) {
      if(position.x<r-1e-7||position.x+r>usable+1e-7||position.y<r-1e-7)continue;
      if(circles.some(c=>Math.hypot(c.x-position.x,c.y-position.y)<c.radius+r+gap-1e-7))continue;
      const left=Math.min(position.x-r,...circles.map(c=>c.x-c.radius));
      const right=Math.max(position.x+r,...circles.map(c=>c.x+c.radius));
      const top=Math.min(position.y-r,...circles.map(c=>c.y-c.radius));
      const height=Math.max(position.y+r,...circles.map(c=>c.y+c.radius))-top;
      const w=right-left;
      const candidateCost=Math.max(w,height)**2+w*height*.1;
      if(candidateCost<cost) {best=position;cost=candidateCost;}
    }
    circles.push({...item,...best});
  }
  if(!circles.length)return {height:0,circles:[]};
  const left=Math.min(...circles.map(c=>c.x-c.radius));
  const right=Math.max(...circles.map(c=>c.x+c.radius));
  const top=Math.min(...circles.map(c=>c.y-c.radius));
  const bottom=Math.max(...circles.map(c=>c.y+c.radius));
  return {height:Math.ceil(bottom-top+2*padding),circles:circles.map(c=>({...c,x:c.x-left+(width-right+left)/2,y:c.y-top+padding}))};
}

export function nestedTopicPages<T extends Topic>(topics:T[],pageSize:number) {
  if(!Number.isInteger(pageSize)||pageSize<1)throw Error('Invalid page size');
  const pages:T[][]=[];
  for(let i=0;i<topics.length;i+=pageSize)pages.push(topics.slice(i,i+pageSize));
  return pages;
}

// 全分野で同じ最大スコアを基準に、表示用の大きさだけを換算する。
export function sizeTopics<T extends Topic>(topics:T[]) {
  const score=(topic:T)=>Math.max(0,Math.min(100,topic.globalImportanceScore??topic.observedAttentionScore??0));
  const maximum=Math.max(1,...topics.map(score));
  return topics.map(topic=>({...topic,sizeScore:score(topic)/maximum*100}));
}

// 円形の外枠ではなく、分野の横幅に最大の小円が収まる共通倍率を使う。
export function fittedRadii(width:number,cfg:DisplayConfig,groups:Topic[][]=[],maxHeight=Infinity) {
  let scale=Math.min(1,Math.max(1,width-2*cfg.parentPadding)/(2*cfg.maxRadius));
  if(Number.isFinite(maxHeight)&&groups.length){
    const fits=(factor:number)=>groups.every(topics=>packTopics(topics,width,{...cfg,minRadius:cfg.minRadius*factor,maxRadius:cfg.maxRadius*factor}).height<=maxHeight);
    if(!fits(scale)){
      let lower=0,upper=scale;
      for(let i=0;i<24;i++){
        const mid=(lower+upper)/2;
        if(fits(mid))lower=mid;else upper=mid;
      }
      scale=lower;
    }
  }
  return {minRadius:cfg.minRadius*scale,maxRadius:cfg.maxRadius*scale};
}
