/** Longest side sent to the server, which shrinks to 1200 px itself; keeps phone photos well under 5 MB. */
const MAX_SIDE = 1600

/**
 * Shrinks a picked photo to a JPEG before upload. Falls back to the original
 * file where the browser can't decode it (the server then decides).
 */
export async function shrinkPhoto(file: File): Promise<Blob> {
  if (typeof createImageBitmap !== 'function') return file
  try {
    const bitmap = await createImageBitmap(file, {
      imageOrientation: 'from-image',
    })
    const scale = Math.min(1, MAX_SIDE / Math.max(bitmap.width, bitmap.height))
    const canvas = document.createElement('canvas')
    canvas.width = Math.round(bitmap.width * scale)
    canvas.height = Math.round(bitmap.height * scale)
    const context = canvas.getContext('2d')
    if (!context) return file
    // Transparent PNGs become white, not black, as JPEGs.
    context.fillStyle = '#fff'
    context.fillRect(0, 0, canvas.width, canvas.height)
    context.drawImage(bitmap, 0, 0, canvas.width, canvas.height)
    bitmap.close()
    const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.88))
    return blob ?? file
  } catch {
    return file
  }
}
