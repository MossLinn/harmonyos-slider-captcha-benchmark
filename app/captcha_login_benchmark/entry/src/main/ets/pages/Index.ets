import { image } from '@kit.ImageKit';

const CAPTCHA_CODES: string[] = ['7K3M', 'A9P4', 'Q2F8'];
const TEST_USER: string = 'testuser';
const TEST_PASSWORD: string = 'pass1234';
const PUZZLE_TARGETS: number[] = [72, 45, 63];
const PUZZLE_TOLERANCE: number = 4;

@Entry
@Component
struct Index {
  @State username: string = '';
  @State password: string = '';
  @State captchaInput: string = '';
  @State captchaIndex: number = 0;
  @State phase: number = 0;
  @State errorMessage: string = '';
  @State sliderValue: number = 0;
  @State sliderVerified: boolean = false;
  @State puzzleIndex: number = 0;
  @State directMode: boolean = false;
  @State directPieceX: number = 24;
  @State directPieceY: number = 92;
  @State directVerified: boolean = false;

  private captchaSettings: RenderingContextSettings = new RenderingContextSettings(true);
  private captchaContext: CanvasRenderingContext2D = new CanvasRenderingContext2D(this.captchaSettings);
  private puzzleSettings: RenderingContextSettings = new RenderingContextSettings(true);
  private puzzleContext: CanvasRenderingContext2D = new CanvasRenderingContext2D(this.puzzleSettings);
  private puzzlePixelMap: image.PixelMap | undefined = undefined;
  private puzzleImageWidth: number = 1672;
  private puzzleImageHeight: number = 941;
  private directDragStartX: number = 24;
  private directDragStartY: number = 92;
  private directDragArmed: boolean = false;

  private drawCaptcha(): void {
    const ctx = this.captchaContext;
    ctx.clearRect(0, 0, 300, 96);
    ctx.fillStyle = '#EEF0FF';
    ctx.fillRect(0, 0, 300, 96);
    ctx.lineWidth = 2;
    const lineColors: string[] = ['#A3A6D9', '#DB7C95', '#6CA8A2', '#DBA85B'];
    for (let i = 0; i < 7; i++) {
      ctx.strokeStyle = lineColors[i % lineColors.length];
      ctx.beginPath();
      ctx.moveTo(8 + i * 37, 10 + (i * 19) % 70);
      ctx.lineTo(52 + i * 35, 82 - (i * 13) % 65);
      ctx.stroke();
    }
    const code = CAPTCHA_CODES[this.captchaIndex];
    const colors: string[] = ['#3540A5', '#B13A5B', '#14756D', '#9A5A10'];
    for (let i = 0; i < code.length; i++) {
      ctx.save();
      ctx.translate(48 + i * 58, 55 + (i % 2 === 0 ? -6 : 7));
      ctx.rotate((i % 2 === 0 ? -1 : 1) * 0.12);
      ctx.fillStyle = colors[i];
      ctx.font = 'bold 38px sans-serif';
      ctx.fillText(code[i], -12, 13);
      ctx.restore();
    }
    for (let i = 0; i < 22; i++) {
      ctx.fillStyle = lineColors[i % lineColors.length];
      ctx.fillRect((i * 47) % 294, (i * 31) % 90, 3, 3);
    }
  }

  private drawPuzzle(): void {
    const ctx = this.puzzleContext;
    ctx.clearRect(0, 0, 330, 168);
    const bitmap = this.puzzlePixelMap;
    if (!bitmap) {
      ctx.fillStyle = '#D8DAE4';
      ctx.fillRect(0, 0, 330, 168);
      return;
    }
    const cropHeight = this.puzzleImageWidth * 168 / 330;
    const cropY = (this.puzzleImageHeight - cropHeight) / 2;
    ctx.drawImage(bitmap, 0, cropY, this.puzzleImageWidth, cropHeight, 0, 0, 330, 168);

    const target = PUZZLE_TARGETS[this.puzzleIndex];
    const gapX = 16 + target * 2.7;
    const sourceX = gapX * this.puzzleImageWidth / 330;
    const sourceY = cropY + 74 * cropHeight / 168;
    const sourceWidth = 46 * this.puzzleImageWidth / 330;
    const sourceHeight = 46 * cropHeight / 168;

    ctx.fillStyle = '#20242C';
    ctx.globalAlpha = 0.48;
    ctx.fillRect(gapX, 74, 46, 46);
    ctx.globalAlpha = 1;
    ctx.strokeStyle = '#FFFFFF';
    ctx.lineWidth = 3;
    ctx.strokeRect(gapX, 74, 46, 46);

    const pieceX = 16 + this.sliderValue * 2.7;
    ctx.drawImage(bitmap, sourceX, sourceY, sourceWidth, sourceHeight, pieceX, 74, 46, 46);
    ctx.strokeStyle = '#FFFFFF';
    ctx.strokeRect(pieceX, 74, 46, 46);
  }

  private traceJigsaw(ctx: CanvasRenderingContext2D, x: number, y: number): void {
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(x + 14, y);
    ctx.bezierCurveTo(x + 12, y - 9, x + 34, y - 9, x + 32, y);
    ctx.lineTo(x + 46, y);
    ctx.lineTo(x + 46, y + 14);
    ctx.bezierCurveTo(x + 37, y + 12, x + 37, y + 34, x + 46, y + 32);
    ctx.lineTo(x + 46, y + 46);
    ctx.lineTo(x + 32, y + 46);
    ctx.bezierCurveTo(x + 34, y + 55, x + 12, y + 55, x + 14, y + 46);
    ctx.lineTo(x, y + 46);
    ctx.lineTo(x, y + 32);
    ctx.bezierCurveTo(x + 9, y + 34, x + 9, y + 12, x, y + 14);
    ctx.closePath();
  }

  private drawDirectPuzzle(): void {
    const ctx = this.puzzleContext;
    ctx.clearRect(0, 0, 330, 168);
    const bitmap = this.puzzlePixelMap;
    if (!bitmap) {
      ctx.fillStyle = '#D8DAE4';
      ctx.fillRect(0, 0, 330, 168);
      return;
    }
    const cropHeight = this.puzzleImageWidth * 168 / 330;
    const cropY = (this.puzzleImageHeight - cropHeight) / 2;
    const gapX = 228;
    const gapY = 48;
    ctx.drawImage(bitmap, 0, cropY, this.puzzleImageWidth, cropHeight, 0, 0, 330, 168);

    this.traceJigsaw(ctx, gapX, gapY);
    ctx.fillStyle = '#161922';
    ctx.globalAlpha = 0.56;
    ctx.fill();
    ctx.globalAlpha = 1;
    ctx.strokeStyle = '#FFFFFF';
    ctx.lineWidth = 3;
    ctx.stroke();

    ctx.save();
    this.traceJigsaw(ctx, this.directPieceX, this.directPieceY);
    ctx.clip();
    ctx.drawImage(bitmap, 0, cropY, this.puzzleImageWidth, cropHeight,
      this.directPieceX - gapX, this.directPieceY - gapY, 330, 168);
    ctx.restore();
    this.traceJigsaw(ctx, this.directPieceX, this.directPieceY);
    ctx.strokeStyle = '#FFFFFF';
    ctx.lineWidth = 3;
    ctx.stroke();
  }

  private resetDirectPuzzle(): void {
    this.directPieceX = 24;
    this.directPieceY = 92;
    this.directVerified = false;
    this.errorMessage = '';
    setTimeout(() => this.drawDirectPuzzle(), 20);
  }

  private validateDirectPuzzle(): void {
    const dx = this.directPieceX - 228;
    const dy = this.directPieceY - 48;
    this.directVerified = Math.sqrt(dx * dx + dy * dy) <= 8;
    this.errorMessage = this.directVerified ? '' : '拼图位置不正确，请重试';
    if (this.directVerified) {
      this.directPieceX = 228;
      this.directPieceY = 48;
      this.drawDirectPuzzle();
    }
  }

  private async loadPuzzleImage(): Promise<void> {
    let resource: Resource = $r('app.media.puzzle_street');
    if (this.puzzleIndex === 1) {
      resource = $r('app.media.puzzle_lake');
    } else if (this.puzzleIndex === 2) {
      resource = $r('app.media.puzzle_cafe');
    }
    const bytes = await getContext(this).resourceManager.getMediaContent(resource);
    const source = image.createImageSource(bytes.buffer as ArrayBuffer);
    this.puzzlePixelMap = await source.createPixelMap();
    const info = this.puzzlePixelMap.getImageInfoSync();
    this.puzzleImageWidth = info.size.width;
    this.puzzleImageHeight = info.size.height;
    this.drawPuzzle();
  }

  private refreshPuzzle(): void {
    this.puzzleIndex = (this.puzzleIndex + 1) % PUZZLE_TARGETS.length;
    this.sliderValue = 0;
    this.sliderVerified = false;
    this.errorMessage = '';
    this.loadPuzzleImage();
  }

  private refreshCaptcha(): void {
    this.captchaIndex = (this.captchaIndex + 1) % CAPTCHA_CODES.length;
    this.captchaInput = '';
    this.errorMessage = '';
    setTimeout(() => this.drawCaptcha(), 20);
  }

  private validateBasicForm(): void {
    if (this.username !== TEST_USER || this.password !== TEST_PASSWORD) {
      this.errorMessage = '账号或密码错误';
      return;
    }
    if (this.captchaInput.toUpperCase() !== CAPTCHA_CODES[this.captchaIndex]) {
      this.errorMessage = '图形验证码错误，请重试';
      this.refreshCaptcha();
      return;
    }
    this.errorMessage = '';
    this.phase = 1;
    this.sliderValue = 0;
    this.sliderVerified = false;
  }

  private validateSlider(value: number): void {
    this.sliderVerified = Math.abs(value - PUZZLE_TARGETS[this.puzzleIndex]) <= PUZZLE_TOLERANCE;
    this.errorMessage = this.sliderVerified ? '' : '拼图位置不正确，请重试';
  }

  private reset(): void {
    this.username = '';
    this.password = '';
    this.captchaInput = '';
    this.sliderValue = 0;
    this.sliderVerified = false;
    this.errorMessage = '';
    this.phase = 0;
    setTimeout(() => this.drawCaptcha(), 20);
  }

  @Builder
  private LoginForm() {
    Column({ space: 18 }) {
      Text('安全登录')
        .fontSize(30)
        .fontWeight(FontWeight.Bold)
        .fontColor('#202238')
      Text('依次完成图形验证码与滑块拼图')
        .fontSize(16)
        .fontColor('#70738A')

      TextInput({ placeholder: '请输入账号', text: this.username })
        .type(InputType.Normal)
        .height(54)
        .backgroundColor(Color.White)
        .borderRadius(12)
        .onChange((value: string) => this.username = value)
      TextInput({ placeholder: '请输入密码', text: this.password })
        .type(InputType.Password)
        .height(54)
        .backgroundColor(Color.White)
        .borderRadius(12)
        .onChange((value: string) => this.password = value)

      Row({ space: 12 }) {
        TextInput({ placeholder: '输入图中字符', text: this.captchaInput })
          .layoutWeight(1)
          .height(54)
          .backgroundColor(Color.White)
          .borderRadius(12)
          .onChange((value: string) => this.captchaInput = value)
        Button('换一张')
          .height(54)
          .fontColor('#5B5CE2')
          .backgroundColor('#E9E9FF')
          .onClick(() => this.refreshCaptcha())
      }

      Canvas(this.captchaContext)
        .width('100%')
        .height(96)
        .borderRadius(12)
        .accessibilityText('图形验证码图片，需要识别四位字符')
        .onReady(() => this.drawCaptcha())

      if (this.errorMessage) {
        Text(this.errorMessage).fontSize(14).fontColor('#C53B54').width('100%')
      }

      Button('验证并继续')
        .width('100%')
        .height(54)
        .fontSize(18)
        .backgroundColor('#5B5CE2')
        .onClick(() => this.validateBasicForm())

      Text('测试账号：testuser　密码：pass1234')
        .fontSize(13)
        .fontColor('#9295A8')
    }
    .width('100%')
  }

  @Builder
  private PuzzleForm() {
    if (this.directMode) {
      this.DirectPuzzleForm()
    } else {
    Column({ space: 18 }) {
      Text('滑块拼图验证')
        .fontSize(28)
        .fontWeight(FontWeight.Bold)
        .fontColor('#202238')
      Text('拖动下方滑块，使照片拼图块与缺口对齐')
        .fontSize(16)
        .fontColor('#70738A')

      Canvas(this.puzzleContext)
        .width('100%')
        .height(168)
        .borderRadius(12)
        .accessibilityText('滑块拼图画面，目标位置仅在图像中可见')
        .onReady(() => this.loadPuzzleImage())

      Button('换一张拼图')
        .height(44)
        .fontColor('#5B5CE2')
        .backgroundColor('#E9E9FF')
        .onClick(() => this.refreshPuzzle())

      Button('测试直接拖动')
        .height(44)
        .fontColor('#5B5CE2')
        .backgroundColor('#E9E9FF')
        .onClick(() => {
          this.directMode = true;
          this.resetDirectPuzzle();
        })

      Slider({ value: this.sliderValue, min: 0, max: 100, step: 1, style: SliderStyle.OutSet })
        .width('100%')
        .trackThickness(12)
        .selectedColor('#5B5CE2')
        .blockColor('#FFFFFF')
        .accessibilityText('拖动滑块完成拼图')
        .onChange((value: number, mode: SliderChangeMode) => {
          this.sliderValue = value;
          this.drawPuzzle();
          if (mode === SliderChangeMode.End) {
            this.validateSlider(value);
          }
        })

      Text(this.sliderVerified ? '验证通过' : '请完成拼图')
        .fontSize(16)
        .fontColor(this.sliderVerified ? '#16865A' : '#70738A')

      if (this.errorMessage) {
        Text(this.errorMessage).fontSize(14).fontColor('#C53B54').width('100%')
      }

      Button('登录')
        .width('100%')
        .height(54)
        .fontSize(18)
        .enabled(this.sliderVerified)
        .backgroundColor(this.sliderVerified ? '#5B5CE2' : '#C7C8D8')
        .onClick(() => this.phase = 2)

      Button('返回上一步')
        .width('100%')
        .height(48)
        .fontColor('#5B5CE2')
        .backgroundColor(Color.Transparent)
        .onClick(() => {
          this.phase = 0;
          this.errorMessage = '';
          setTimeout(() => this.drawCaptcha(), 20);
        })
    }
    .width('100%')
    }
  }

  @Builder
  private DirectPuzzleForm() {
    Column({ space: 18 }) {
      Text('直接拖动拼图')
        .fontSize(28)
        .fontWeight(FontWeight.Bold)
        .fontColor('#202238')
      Text('抓住左侧不规则拼图块，拖入右上方缺口')
        .fontSize(16)
        .fontColor('#70738A')

      Canvas(this.puzzleContext)
        .width('100%')
        .height(168)
        .borderRadius(12)
        .accessibilityText('可直接拖动的不规则拼图画面')
        .onReady(() => this.loadPuzzleImage().then(() => this.drawDirectPuzzle()))
        .gesture(
          PanGesture({ direction: PanDirection.All })
            .onActionStart((event: GestureEvent) => {
              const finger = event.fingerList[0];
              this.directDragArmed = finger.localX >= this.directPieceX - 8 &&
                finger.localX <= this.directPieceX + 54 &&
                finger.localY >= this.directPieceY - 8 &&
                finger.localY <= this.directPieceY + 55;
              this.directDragStartX = this.directPieceX;
              this.directDragStartY = this.directPieceY;
            })
            .onActionUpdate((event: GestureEvent) => {
              if (this.directDragArmed) {
                this.directPieceX = this.directDragStartX + event.offsetX;
                this.directPieceY = this.directDragStartY + event.offsetY;
                this.drawDirectPuzzle();
              }
            })
            .onActionEnd(() => {
              if (this.directDragArmed) {
                this.validateDirectPuzzle();
              }
              this.directDragArmed = false;
            })
        )

      Text(this.directVerified ? '直接拖动验证通过' : '请将拼图块拖入缺口')
        .fontSize(16)
        .fontColor(this.directVerified ? '#16865A' : '#70738A')

      if (this.errorMessage) {
        Text(this.errorMessage).fontSize(14).fontColor('#C53B54').width('100%')
      }

      Button('重置直接拖动')
        .width('100%')
        .height(48)
        .fontColor('#5B5CE2')
        .backgroundColor('#E9E9FF')
        .onClick(() => this.resetDirectPuzzle())

      Button('返回滑块模式')
        .width('100%')
        .height(48)
        .fontColor('#5B5CE2')
        .backgroundColor(Color.Transparent)
        .onClick(() => {
          this.directMode = false;
          this.errorMessage = '';
          setTimeout(() => this.drawPuzzle(), 20);
        })
    }
    .width('100%')
  }

  @Builder
  private SuccessView() {
    Column({ space: 22 }) {
      Text('✓')
        .fontSize(72)
        .fontWeight(FontWeight.Bold)
        .fontColor('#16865A')
      Text('登录成功')
        .fontSize(30)
        .fontWeight(FontWeight.Bold)
        .fontColor('#202238')
      Text('图形验证码和滑块拼图均已通过')
        .fontSize(16)
        .fontColor('#70738A')
      Button('重新测试')
        .width('100%')
        .height(54)
        .backgroundColor('#5B5CE2')
        .onClick(() => this.reset())
    }
    .width('100%')
  }

  build() {
    Scroll() {
      Column() {
        Column() {
          if (this.phase === 0) {
            this.LoginForm()
          } else if (this.phase === 1) {
            this.PuzzleForm()
          } else {
            this.SuccessView()
          }
        }
        .width('100%')
        .padding(28)
        .backgroundColor('#F6F7FB')
      }
      .width('100%')
      .height('100%')
      .justifyContent(FlexAlign.Center)
    }
    .width('100%')
    .height('100%')
    .backgroundColor('#F6F7FB')
  }
}
