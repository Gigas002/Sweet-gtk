// Run by tests/compare.py in a private headless GNOME Shell: opens the shell's main views one
// after another, screenshots each into $SWEET_SHOT_DIR, then quits the shell.
import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import Shell from 'gi://Shell';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

const OUT = GLib.getenv('SWEET_SHOT_DIR');

function wait(ms) {
    return new Promise(resolve => GLib.timeout_add(GLib.PRIORITY_DEFAULT, ms, () => {
        resolve();
        return GLib.SOURCE_REMOVE;
    }));
}

async function shot(name) {
    await wait(1500); // let animations finish
    const file = Gio.File.new_for_path(`${OUT}/${name}.png`);
    const stream = file.replace(null, false, Gio.FileCreateFlags.NONE, null);
    const screenshot = new Shell.Screenshot();
    await new Promise((resolve, reject) => screenshot.screenshot(false, stream, (s, result) => {
        try {
            s.screenshot_finish(result);
            resolve();
        } catch (e) {
            reject(e);
        }
    }));
    stream.close(null);
}

export default class ShellShot extends Extension {
    enable() {
        this._run()
            .catch(e => console.error(`shell-shot: ${e}\n${e.stack}`))
            .finally(() => global.context.terminate());
    }

    disable() {}

    async _run() {
        await wait(3000);
        await shot('welcome'); // the first-login welcome dialog, if the shell shows one
        for (const dialog of Main.layoutManager.modalDialogGroup.get_children())
            dialog.close?.();
        Main.notify('Sweet test', 'A notification body, to show the banner');
        await shot('desktop');
        Main.overview.show();
        await shot('overview');
        Main.overview.showApps();
        await shot('apps');
        Main.overview.hide();
        await wait(800);
        for (const [name, indicator] of [['quick-settings', 'quickSettings'], ['calendar', 'dateMenu']]) {
            const menu = Main.panel.statusArea[indicator].menu;
            menu.open();
            await shot(name);
            menu.close();
        }
    }
}
