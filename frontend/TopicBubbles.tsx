import React,{useEffect,useRef,useState} from 'react';
import {groupTopics,packTopics,nestedTopicPages,fittedRadii,sizeTopics} from './topic-layout.ts';
import type {DisplayConfig,Topic} from './topic-layout.ts';
import type {Data} from './helpers.ts';

type Props={topics:Data[];onSelect:(topic:Data)=>void;displayConfig:DisplayConfig;color?:string;fields?:string[];renderLabel?:(topic:Data,maxLines:number)=>React.ReactNode};

function Cluster({label,topics,index,onSelect,displayConfig,color,layoutGroups,heightBudget,renderLabel}:Props&{label:string;index:number;layoutGroups:Topic[][];heightBudget?:number}) {
  const canvas=useRef<HTMLDivElement>(null);
  const [width,setWidth]=useState(320);
  const [page,setPage]=useState(0);
  useEffect(()=>{
    const element=canvas.current;
    if(!element)return;
    const observer=new ResizeObserver(entries=>setWidth(Math.max(1,entries[0].contentRect.width)));
    observer.observe(element);
    return ()=>observer.disconnect();
  },[]);
  const pages=nestedTopicPages<Data & {topicId:string}>(topics.map(t=>({...t,topicId:t.topicId})),displayConfig.pageSize);
  const current=Math.min(page,pages.length-1);
  const visible=pages[current]||[];
  const fitted=fittedRadii(width,displayConfig,layoutGroups,heightBudget);
  const layout=packTopics(visible,width,{...displayConfig,...fitted});
  const zoom=(displayConfig.zoomPercent??100)/100;
  const leftEdge=Math.min(...layout.circles.map(c=>c.x-c.radius));
  const rightEdge=Math.max(...layout.circles.map(c=>c.x+c.radius));
  const canvasWidth=zoom>1?Math.max(width,(rightEdge-leftEdge)*zoom+2*displayConfig.parentPadding):width;
  const offsetX=zoom>1?(canvasWidth-(rightEdge-leftEdge)*zoom)/2-leftEdge*zoom:0;
  const positions=new Map(layout.circles.map(c=>[c.topicId,c]));
  return <section className={'topicCluster clusterColor'+index%5} aria-label={label+'の話題'}>
    <h2 style={{color:color||undefined}}>{label}</h2>
    <div ref={canvas} className="clusterViewport">
      <div className="clusterCanvas" style={{width:canvasWidth,height:layout.height*zoom}}>
      {visible.map(topic=>{
        const circle=positions.get(topic.topicId)!;
        const value=topic.globalImportanceScore??topic.observedAttentionScore;
        const score=value==null?'—':String(Math.round(value));
        const diameter=circle.radius*2*zoom;
        const fontSize=Math.max(displayConfig.labelMinFontSize,Math.min(displayConfig.labelMaxFontSize,circle.radius*2*displayConfig.labelFontRatio))*Math.sqrt(zoom);
        const titleLines=Math.max(1,Math.min(displayConfig.labelMaxLines,Math.floor((diameter-27-Math.max(9,fontSize*.7)*1.2)/(fontSize*1.2))));
        return <button key={topic.topicId} className="bubble" aria-label={topic.title+' — '+score} title={topic.title+' — '+score}
          style={{width:diameter,height:diameter,left:(circle.x-circle.radius)*zoom+offsetX,top:(circle.y-circle.radius)*zoom,background:color||undefined,fontSize}}
          onClick={()=>onSelect(topic)}>
          {renderLabel?renderLabel(topic,titleLines):<b style={{WebkitLineClamp:titleLines}}>{topic.title}</b>}<em>{score}</em>
        </button>;
      })}
      </div>
    </div>
    {pages.length>1&&<div className="clusterPager"><button disabled={current===0} onClick={()=>setPage(current-1)} aria-label={label+'の前の話題'}>前へ</button><span aria-live="polite">{current+1} / {pages.length}</span><button disabled={current===pages.length-1} onClick={()=>setPage(current+1)} aria-label={label+'の次の話題'}>次へ</button></div>}
  </section>;
}

export function TopicBubbles(props:Props) {
  const cfg=props.displayConfig;
  const map=useRef<HTMLDivElement>(null);
  const [heightBudget,setHeightBudget]=useState<number>();
  const collected=groupTopics(sizeTopics(props.topics.map(t=>({...t,topicId:t.topicId}))),cfg.aliases,cfg.fields);
  const fields=props.fields?.length?props.fields:cfg.fields;
  const groups=fields.map(label=>collected.find(g=>g.label===label)||{label,topics:[]});
  const layoutGroups=groups.flatMap(group=>nestedTopicPages(group.topics,cfg.pageSize));
  useEffect(()=>{
    const element=map.current,grid=element?.querySelector('.bubbles');
    if(!element||!grid)return;
    let measuredWidth=0;
    const measure=()=>{
      const width=grid.getBoundingClientRect().width;
      // アドレスバーやキーボードによる高さだけの変化では、現在の配置を保つ。
      if(width<=0||width===measuredWidth)return;
      measuredWidth=width;
      if(getComputedStyle(grid).gridTemplateColumns.split(' ').length!==1){setHeightBudget(undefined);return}
      const gap=parseFloat(getComputedStyle(grid).rowGap)||0;
      const headings=[...grid.querySelectorAll('h2')].reduce((sum,h)=>{
        const style=getComputedStyle(h);
        return sum+h.getBoundingClientRect().height+(parseFloat(style.marginTop)||0)+(parseFloat(style.marginBottom)||0);
      },0);
      const pagers=[...grid.querySelectorAll('.clusterPager')].reduce((sum,p)=>sum+p.getBoundingClientRect().height+(parseFloat(getComputedStyle(p).marginTop)||0),0);
      const top=element.getBoundingClientRect().top+window.scrollY;
      const main=element.closest('main');
      const bottom=main?parseFloat(getComputedStyle(main).paddingBottom)||0:0;
      const chrome=top+headings+pagers+gap*Math.max(0,groups.length-1)+bottom;
      setHeightBudget(Math.max(2*cfg.parentPadding+1,(window.innerHeight*cfg.mobileViewportScreens-chrome)/groups.length));
    };
    const observer=new ResizeObserver(measure);
    observer.observe(grid);window.addEventListener('resize',measure);measure();
    return ()=>{observer.disconnect();window.removeEventListener('resize',measure)};
  },[cfg.mobileViewportScreens,cfg.parentPadding,groups.length]);
  return <div ref={map} className="topicMap" aria-label="分野ごとにまとめたニュース">
    <div className="bubbles">{groups.map(group=>group.topics.length?<Cluster {...props} layoutGroups={layoutGroups} heightBudget={heightBudget} key={group.label} label={group.label} topics={group.topics} index={Math.max(0,cfg.fields.indexOf(group.label))}/>:<section key={group.label} className={'topicCluster fieldEmpty clusterColor'+Math.max(0,cfg.fields.indexOf(group.label))%5}><h2>{group.label}</h2><span className="emptyMark" aria-label="未取得">—</span></section>)}</div>
  </div>;
}
