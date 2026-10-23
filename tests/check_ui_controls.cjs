// Execute the actual inline handlers with HTMLButtonElement.command in scope.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const html = fs.readFileSync(__dirname + '/../web/dataset-desk/index.html', 'utf8');
new vm.Script(fs.readFileSync(__dirname + '/../web/dataset-desk/assets/desk.js', 'utf8'));
const calls = [];
const globals = {sendControl: (action, body) => calls.push({action, body}), $: () => ({value: '60'})};
globals.window = globals;
const button = {command: ''};
const execute = text => new Function('button', 'globals', `with(globals){with(button){${text}}}`)(button, globals);
assert.throws(() => execute("command('start')"), TypeError);
for (const id of ['start', 'stop', 'disconnect']) {
    const tag = html.match(new RegExp(`<button\\b[^>]*id="${id}"[^>]*>`))[0];
    execute(tag.match(/onclick="([^"]+)"/)[1]);
}
assert.deepEqual(calls, [{action: 'start', body: {duration: 60}}, {action: 'stop', body: undefined}, {action: 'disconnect', body: undefined}]);
console.log('PASS: old command collision reproduced; actual Start/Stop/Disconnect handlers dispatch correctly; page JavaScript parses; no hardware requests sent.');
