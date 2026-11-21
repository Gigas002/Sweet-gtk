// Run by tests/compare.py in a private headless GNOME Shell: opens the shell's views one after
// another, screenshots each into $SWEET_SHOT_DIR as NAME.png, then quits the shell. A view that
// fails is logged ("shell-shot: NAME: ...") and skipped.
import Clutter from 'gi://Clutter';
import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import Shell from 'gi://Shell';
import St from 'gi://St';
import * as AltTab from 'resource:///org/gnome/shell/ui/altTab.js';
import * as CheckBox from 'resource:///org/gnome/shell/ui/checkBox.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as ModalDialog from 'resource:///org/gnome/shell/ui/modalDialog.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

const OUT = GLib.getenv('SWEET_SHOT_DIR');
const TESTS = GLib.getenv('SWEET_TESTS_DIR');

function wait(ms) {
    return new Promise(resolve => GLib.timeout_add(GLib.PRIORITY_DEFAULT, ms, () => {
        resolve();
        return GLib.SOURCE_REMOVE;
    }));
}

async function screenshot(name) {
    await wait(1500); // let animations finish
    const file = Gio.File.new_for_path(`${OUT}/${name}.png`);
    const stream = file.replace(null, false, Gio.FileCreateFlags.NONE, null);
    const shooter = new Shell.Screenshot();
    await new Promise((resolve, reject) => shooter.screenshot(false, stream, (s, result) => {
        try {
            s.screenshot_finish(result);
            resolve();
        } catch (e) {
            reject(e);
        }
    }));
    stream.close(null);
}

// Each view: [name, async function that opens it and returns a function that closes it]
const VIEWS = [
    ['desktop', async () => {
        Main.notify('Sweet test', 'A notification body, to show the banner');
    }],
    ['overview', async () => {
        Main.overview.show();
        return () => Main.overview.hide();
    }],
    ['search', async () => {
        Main.overview.show();
        await wait(800);
        Main.overview.searchEntry.set_text('set');
        return () => {
            Main.overview.searchEntry.set_text('');
            Main.overview.hide();
        };
    }],
    ['apps', async () => {
        Main.overview.showApps();
        return () => Main.overview.hide();
    }],
    ['app-menu', async () => {
        Main.overview.show();
        await wait(800);
        const item = Main.overview.dash._box.get_children().find(c => c.child?.app);
        item.child.popupMenu();
        return () => {
            item.child._menu?.close();
            Main.overview.hide();
        };
    }],
    ['quick-settings', async () => {
        const menu = Main.panel.statusArea.quickSettings.menu;
        menu.open();
        return () => menu.close();
    }],
    ['calendar', async () => {
        const menu = Main.panel.statusArea.dateMenu.menu;
        menu.open();
        return () => menu.close();
    }],
    ['dialog', async () => {
        const dialog = new ModalDialog.ModalDialog();
        const box = new St.BoxLayout({style: 'spacing: 12px'});
        if ('orientation' in box)
            box.orientation = Clutter.Orientation.VERTICAL; // GNOME 48+
        else
            box.vertical = true;
        box.add_child(new St.Label({text: 'A dialog with every kind of control', style_class: 'message-dialog-title'}));
        const on = new CheckBox.CheckBox('A checked box');
        on.checked = true;
        box.add_child(on);
        box.add_child(new CheckBox.CheckBox('An unchecked box'));
        box.add_child(new St.Entry({text: 'An entry', style_class: 'prompt-dialog-password-entry'}));
        dialog.contentLayout.add_child(box);
        dialog.setButtons([{label: 'Cancel', action: () => {}}, {label: 'Default', action: () => {}, default: true}]);
        dialog.open();
        return () => dialog.close();
    }],
    ['osd', async () => {
        Main.osdWindowManager.showAll(Gio.ThemedIcon.new('audio-volume-medium-symbolic'), 'Volume', 0.6, 1);
    }],
    ['switcher', async () => {
        const popup = new AltTab.WindowSwitcherPopup();
        popup.show(false, 'switch-windows', 0);
        return () => popup.destroy();
    }],
    ['screenshot-ui', async () => {
        Main.screenshotUI.open();
        return () => Main.screenshotUI.close(true);
    }],
];

export default class ShellShot extends Extension {
    enable() {
        this._run()
            .catch(e => console.error(`shell-shot: ${e}\n${e.stack}`))
            .finally(() => global.context.terminate());
    }

    disable() {}

    async _run() {
        await wait(3000);
        await screenshot('welcome'); // the first-login welcome dialog, if the shell shows one
        for (const dialog of Main.layoutManager.modalDialogGroup.get_children())
            dialog.close?.();
        // two windows, for the overview's window picker and the switcher
        const windows = ['First window', 'Second window'].map(title =>
            Gio.Subprocess.new(['python3', `${TESTS}/window.py`, title], Gio.SubprocessFlags.NONE));
        await wait(2000);
        for (const [name, open] of VIEWS) {
            try {
                const close = await open();
                await screenshot(name);
                close?.();
                await wait(800);
            } catch (e) {
                console.error(`shell-shot: ${name}: ${e}\n${e.stack}`);
            }
        }
        windows.forEach(w => w.force_exit());
    }
}
