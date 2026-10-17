// A loud, repeating chime for new orders, made with Web Audio so it needs no
// sound files. Browsers only allow audio after a click, so the portal asks the
// user to turn sound on once; after that `unlocked` stays true.

const PATTERN = [
  { freq: 988, at: 0 }, // B5
  { freq: 1319, at: 0.18 }, // E6
  { freq: 988, at: 0.36 },
  { freq: 1319, at: 0.54 },
]
const REPEAT_MS = 2500

export class OrderAlarm {
  private context: AudioContext | null = null
  private timer: ReturnType<typeof setInterval> | null = null

  get unlocked(): boolean {
    return this.context?.state === 'running'
  }

  get ringing(): boolean {
    return this.timer !== null
  }

  /** Call from a click handler. */
  async unlock(): Promise<boolean> {
    try {
      this.context ??= new AudioContext()
      await this.context.resume()
    } catch {
      return false
    }
    return this.unlocked
  }

  start() {
    if (this.timer) return
    this.chime()
    this.timer = setInterval(() => this.chime(), REPEAT_MS)
  }

  stop() {
    if (this.timer) clearInterval(this.timer)
    this.timer = null
  }

  private chime() {
    const ctx = this.context
    if (!ctx || ctx.state !== 'running') return
    const now = ctx.currentTime
    for (const note of PATTERN) {
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.type = 'square' // cuts through kitchen noise better than a sine
      osc.frequency.value = note.freq
      gain.gain.setValueAtTime(0.0001, now + note.at)
      gain.gain.exponentialRampToValueAtTime(0.6, now + note.at + 0.02)
      gain.gain.exponentialRampToValueAtTime(0.0001, now + note.at + 0.16)
      osc.connect(gain).connect(ctx.destination)
      osc.start(now + note.at)
      osc.stop(now + note.at + 0.17)
    }
  }
}
