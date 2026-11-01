import {createElement as el} from 'react';
import type {ReactNode} from 'react';

const precedence:Record<string,number>={'=':1,'+':2,'-':2,'−':2,'×':3,'/':3};

// Parse only the arithmetic notation returned by Backend; never execute it.
export function Formula({line}:{line:string}){
 const condition=line.match(/^【[^】]+】/)?.[0];
 const tokens=(condition?line.slice(condition.length):line).match(/\d+(?:\.\d+)?|[\p{L}₁]+|[=+×/(),−-]/gu)||[];
 let index=0;
 const row=(...children:ReactNode[])=>el('mrow',null,...children);
 function atom():ReactNode{
  const token=tokens[index++];
  if(token==='('){const value=expression(0);index++;return row(el('mo',null,'('),value,el('mo',null,')'))}
  const symbol=token==='P前期'?el('msub',null,el('mi',null,'P'),el('mtext',null,'前期'))
   :token==='round₁'?el('msub',null,el('mi',null,'round'),el('mn',null,'1'))
   :el(/^\d/.test(token||'')?'mn':'mi',null,token);
  if(tokens[index]!=='(')return symbol;
  index++;
  const args:ReactNode[]=[expression(0)];
  while(tokens[index]===','){index++;args.push(el('mo',{key:index},','),expression(0))}
  index++;
  return row(symbol,el('mo',null,'('),...args,el('mo',null,')'));
 }
 function expression(min:number):ReactNode{
  let left=atom();
  while(index<tokens.length&&(precedence[tokens[index]]||0)>min){
   const operator=tokens[index++];
   const right=expression(precedence[operator]);
   left=operator==='/'?el('mfrac',null,left,right):row(left,el('mo',null,operator),right);
  }
  return left;
 }
 return <div className="formulaLine">{condition&&<b>{condition}</b>}<div className="formulaScroll">
  {el('math',{xmlns:'http://www.w3.org/1998/Math/MathML',display:'block','aria-label':line},expression(0))}
 </div></div>;
}
