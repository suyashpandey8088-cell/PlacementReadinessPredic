import {test} from 'node:test';
import assert from 'node:assert/strict';
import {CATEGORY_NAMES,HISTORY_KEY,isRecord,readHistory,saveAssessment,clearHistory,historyCsv,csvCell,parseBackup} from '../../web/storage.js';
class MemoryStorage {
  constructor(){this.data=new Map();}
  getItem(key){return this.data.get(key)??null;}
  setItem(key,value){this.data.set(key,value);}
  removeItem(key){this.data.delete(key);}
}
function record(id='550e8400-e29b-41d4-a716-446655440000'){
  return {id,created_at:'2026-10-22T05:00:00Z',inputs:{cgpa:7,mock:null},score:50,band:'Developing',scoring_version:'1.0',categories:Object.fromEntries(CATEGORY_NAMES.map(c=>[c,50])),missing_optional:['mock'],recommendations:[],plan:[]};
}
test('save is explicit, persistent and idempotent',()=>{
  const storage=new MemoryStorage();assert.deepEqual(readHistory(storage),[]);
  saveAssessment(record(),storage);saveAssessment(record(),storage);
  assert.equal(readHistory(storage).length,1);
  assert.equal(readHistory(storage)[0].inputs.mock,null);
  clearHistory(storage);assert.deepEqual(readHistory(storage),[]);
});
test('separate browser stores cannot see each other',()=>{
  const a=new MemoryStorage(),b=new MemoryStorage();saveAssessment(record(),a);assert.equal(readHistory(b).length,0);
});
test('invalid records and corrupt history are rejected',()=>{
  assert.equal(isRecord({...record(),score:101}),false);
  assert.equal(isRecord({...record(),categories:{}}),false);
  const storage=new MemoryStorage();storage.setItem(HISTORY_KEY,'{}');
  assert.throws(()=>readHistory(storage));assert.throws(()=>saveAssessment({},storage));
});
test('CSV retains actual fields and escapes spreadsheet formulas',()=>{
  const csv=historyCsv([record()]);assert.match(csv,/readiness_score/);assert.match(csv,/cgpa/);assert.match(csv,/50/);
  assert.equal(csvCell('=HYPERLINK("evil")'),'"\'=HYPERLINK(""evil"")"');
});
test('backup validation accepts valid backup and rejects malformed or duplicate content',()=>{
  const backup={version:2,assessments:[record()]};assert.equal(parseBackup(JSON.stringify(backup)).length,1);
  assert.throws(()=>parseBackup('{no'));assert.throws(()=>parseBackup(JSON.stringify({...backup,version:1})));
  assert.throws(()=>parseBackup(JSON.stringify({...backup,assessments:[record(),record()]})));
  assert.throws(()=>parseBackup('x'.repeat(2_000_001)));
});
test('storage limits fail explicitly, without silent deletion',()=>{
  const storage=new MemoryStorage();const records=Array.from({length:200},(_,i)=>record(`assessment-${i}`));
  storage.setItem(HISTORY_KEY,JSON.stringify(records));assert.throws(()=>saveAssessment(record(),storage),/200/);
  assert.equal(readHistory(storage).length,200);
});
