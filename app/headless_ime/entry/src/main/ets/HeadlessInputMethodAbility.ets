import { InputMethodExtensionAbility, inputMethodEngine } from '@kit.IMEKit';
import { hilog } from '@kit.PerformanceAnalysisKit';
import { Want } from '@kit.AbilityKit';

const DOMAIN: number = 0x484D;
const TAG: string = 'HeadlessIme';
export default class HeadlessInputMethodAbility extends InputMethodExtensionAbility {
  private ime: inputMethodEngine.InputMethodAbility = inputMethodEngine.getInputMethodAbility();
  private inputClient?: inputMethodEngine.InputClient;
  private keyboardController?: inputMethodEngine.KeyboardController;

  private readonly onInputStart = (controller: inputMethodEngine.KeyboardController,
    client: inputMethodEngine.InputClient): void => {
    this.keyboardController = controller;
    this.inputClient = client;
    controller.hide().catch((error: Error) => {
      hilog.warn(DOMAIN, TAG, 'Keyboard was already hidden: %{public}s', error.message);
    });
  }

  private readonly onInputStop = (): void => {
    this.inputClient = undefined;
    this.keyboardController = undefined;
  }

  onCreate(want: Want): void {
    hilog.info(DOMAIN, TAG, 'Created: %{public}s', want.abilityName ?? 'unknown');
    this.ime.on('inputStart', this.onInputStart);
    this.ime.on('inputStop', this.onInputStop);
  }

  onDestroy(): void {
    this.ime.off('inputStart', this.onInputStart);
    this.ime.off('inputStop', this.onInputStop);
    this.inputClient = undefined;
  }
}
