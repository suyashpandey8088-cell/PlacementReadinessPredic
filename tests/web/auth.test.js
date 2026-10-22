import {test} from 'node:test';
import assert from 'node:assert/strict';
import {normalizeEmail,validateEmail,passwordProblem,accountInitial,safeNextPath,shortEmail} from '../../web/auth-utils.js';

test('email normalization is explicit and conservative',()=>{
  assert.equal(normalizeEmail('  Student@Example.COM '),'student@example.com');
  assert.equal(normalizeEmail(null),'');
  assert.equal(validateEmail('student@example.com'),true);
  assert.equal(validateEmail('not-an-email'),false);
  assert.equal(validateEmail('a@b.c'),false);
  assert.equal(validateEmail(`${'a'.repeat(250)}@x.com`),false);
});

test('password rules match the server minimum and maximum',()=>{
  assert.match(passwordProblem('short'),/8 characters/);
  assert.match(passwordProblem('        '),/Enter a password/);
  assert.match(passwordProblem('x'.repeat(129)),/shorter/);
  assert.equal(passwordProblem('a good passphrase'),'');
});

test('account initials do not invent profile names',()=>{
  assert.equal(accountInitial('student@example.com'),'S');
  assert.equal(accountInitial('éclair@example.com'),'É');
  assert.equal(accountInitial(''),'?');
  assert.equal(accountInitial(null),'?');
});

test('next paths stay internal and never return to login',()=>{
  assert.equal(safeNextPath('/results'),'/results');
  assert.equal(safeNextPath('/results?tab=plan'),'/results?tab=plan');
  assert.equal(safeNextPath('https://evil.example/steal'),'/progress');
  assert.equal(safeNextPath('//evil.example/steal'),'/progress');
  assert.equal(safeNextPath('/\\evil.example'),'/progress');
  assert.equal(safeNextPath('/login?mode=signup'),'/progress');
  assert.equal(safeNextPath(null),'/progress');
});

test('long account labels are shortened without altering the email',()=>{
  assert.equal(shortEmail('student@example.com',30),'student@example.com');
  assert.match(shortEmail('a-very-long-student-address@example.com',12),/…$/);
});
