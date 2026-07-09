param(
  [Parameter(Mandatory=$true)][string]$InputJson,
  [Parameter(Mandatory=$true)][string]$OutputDir
)

Add-Type -AssemblyName System.Drawing

$json = Get-Content -Raw -Encoding UTF8 $InputJson | ConvertFrom-Json
New-Item -ItemType Directory -Force $OutputDir | Out-Null

$script:Ink = "#111111"
$script:Paper = "#FFFFFA"
$script:Black = "#050505"
$script:Blue = "#1A72B8"
$script:Red = "#C9362C"
$script:CanvasW = 1080
$script:PaperW = 560
$script:PaperX = [int](($script:CanvasW - $script:PaperW) / 2)
$script:CanvasPadY = 44
$script:AssetDir = Join-Path (Split-Path -Parent (Split-Path -Parent $PSCommandPath)) "assets"
$script:TopSkinPath = Join-Path $script:AssetDir "receipt-skin-top.png"
$script:MidSkinPath = Join-Path $script:AssetDir "receipt-skin-mid.png"
$script:BottomSkinPath = Join-Path $script:AssetDir "receipt-skin-bottom.png"
$script:IllustrationPath = $null
if (($json.PSObject.Properties.Name -contains "persona_illustration_asset") -and $json.persona_illustration_asset) {
  $candidate = [string]$json.persona_illustration_asset
  if (Test-Path -LiteralPath $candidate) {
    $script:IllustrationPath = (Resolve-Path -LiteralPath $candidate).Path
  }
}

function Color-Hex([string]$hex) {
  return [System.Drawing.ColorTranslator]::FromHtml($hex)
}

function New-Bitmap([int]$w, [int]$h, [bool]$transparent = $false) {
  if ($transparent) {
    $bmp = [System.Drawing.Bitmap]::new($w, $h, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
  } else {
    $bmp = [System.Drawing.Bitmap]::new($w, $h)
  }
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::None
  $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::NearestNeighbor
  $g.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::Half
  $g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::SingleBitPerPixelGridFit
  return @($bmp, $g)
}

function Save-Png($bmp, $g, [string]$path) {
  $g.Dispose()
  $bmp.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
  $bmp.Dispose()
}

function New-Font([float]$size, [string]$style = "Regular") {
  $fontStyle = [System.Drawing.FontStyle]::$style
  return [System.Drawing.Font]::new("Consolas", $size, $fontStyle, [System.Drawing.GraphicsUnit]::Pixel)
}

function Draw-Text($g, [string]$text, [float]$x, [float]$y, [float]$size, [string]$color = "#111111", [string]$style = "Regular") {
  $font = New-Font $size $style
  $brush = [System.Drawing.SolidBrush]::new((Color-Hex $color))
  $g.DrawString($text, $font, $brush, $x, $y)
  $brush.Dispose()
  $font.Dispose()
}

function Draw-Centered($g, [string]$text, [float]$x, [float]$y, [float]$w, [float]$size, [string]$color = "#111111", [string]$style = "Regular") {
  $font = New-Font $size $style
  $brush = [System.Drawing.SolidBrush]::new((Color-Hex $color))
  $fmt = [System.Drawing.StringFormat]::new()
  $fmt.Alignment = [System.Drawing.StringAlignment]::Center
  $fmt.LineAlignment = [System.Drawing.StringAlignment]::Near
  $rect = [System.Drawing.RectangleF]::new($x, $y, $w, ($size * 1.55))
  $g.DrawString($text, $font, $brush, $rect, $fmt)
  $fmt.Dispose()
  $brush.Dispose()
  $font.Dispose()
}

function Fill-Rect($g, [float]$x, [float]$y, [float]$w, [float]$h, [string]$color) {
  $brush = [System.Drawing.SolidBrush]::new((Color-Hex $color))
  $g.FillRectangle($brush, $x, $y, $w, $h)
  $brush.Dispose()
}

function Stroke-Rect($g, [float]$x, [float]$y, [float]$w, [float]$h, [string]$color = "#111111", [float]$width = 2) {
  $pen = [System.Drawing.Pen]::new((Color-Hex $color), $width)
  $g.DrawRectangle($pen, $x, $y, $w, $h)
  $pen.Dispose()
}

function Draw-DotRule($g, [float]$x, [float]$y, [float]$w) {
  $brush = [System.Drawing.SolidBrush]::new((Color-Hex $script:Ink))
  $cursor = $x
  while ($cursor -lt ($x + $w)) {
    $g.FillEllipse($brush, $cursor, $y, 5, 5)
    $cursor += 15
  }
  $brush.Dispose()
}

function Draw-DotTrail($g, [float]$x1, [float]$x2, [float]$y) {
  if ($x2 -le ($x1 + 8)) { return }
  $brush = [System.Drawing.SolidBrush]::new((Color-Hex $script:Ink))
  $cursor = $x1
  while ($cursor -lt $x2) {
    $g.FillEllipse($brush, $cursor, $y, 3.4, 3.4)
    $cursor += 12
  }
  $brush.Dispose()
}

function Short-Label([string]$label) {
  $upper = $label.ToUpper()
  if ($upper -like "RESEARCH*") { return "RESEARCH & PATTERNING" }
  if ($upper -like "WRITING*") { return "WRITING / DOCUMENTATION" }
  if ($upper -like "DEBUG*") { return "DEBUG / PROBLEM SOLVING" }
  if ($upper -like "CREATIVE*") { return "CREATIVE DIRECTION" }
  if ($upper -like "DESIGN*") { return "DESIGN / STRUCTURE" }
  if ($upper -like "MAINTENANCE*") { return "MAINTENANCE / CLEANUP" }
  if ($label.Length -gt 28) { return $label.Substring(0, 28) }
  return $label
}

function Dotted-Row($g, [string]$label, [string]$value, [float]$x, [float]$y, [float]$w, [float]$size = 19) {
  $label = Short-Label $label
  Draw-Text $g $label $x $y $size
  $font = New-Font $size "Regular"
  $brush = [System.Drawing.SolidBrush]::new((Color-Hex $script:Ink))
  $fmt = [System.Drawing.StringFormat]::new()
  $fmt.Alignment = [System.Drawing.StringAlignment]::Far
  $rect = [System.Drawing.RectangleF]::new($x, $y, $w, ($size * 1.55))
  $valueSize = $g.MeasureString($value, $font)
  $dotStart = $x + 172
  $dotEnd = $x + $w - $valueSize.Width - 12
  Draw-DotTrail $g $dotStart $dotEnd ($y + ($size * 0.76))
  $g.DrawString($value, $font, $brush, $rect, $fmt)
  $fmt.Dispose()
  $brush.Dispose()
  $font.Dispose()
}

function Seed-Value([string]$seed) {
  $v = 17
  foreach ($ch in $seed.ToCharArray()) {
    $v = (($v * 31) + [int][char]$ch) % 2147483647
  }
  return $v
}

function Draw-Barcode($g, [float]$x, [float]$y, [float]$w, [float]$h, [string]$seed) {
  $rand = [System.Random]::new((Seed-Value $seed))
  $brush = [System.Drawing.SolidBrush]::new((Color-Hex $script:Ink))
  $cursor = $x
  while ($cursor -lt ($x + $w)) {
    $bar = $rand.Next(2, 7)
    $gap = $rand.Next(2, 5)
    $g.FillRectangle($brush, $cursor, $y, $bar, $h)
    $cursor += $bar + $gap
  }
  $brush.Dispose()
}

function Draw-SkinPaper($g, [int]$paperH) {
  if (-not ((Test-Path -LiteralPath $script:TopSkinPath) -and (Test-Path -LiteralPath $script:MidSkinPath) -and (Test-Path -LiteralPath $script:BottomSkinPath))) {
    Fill-Rect $g $script:PaperX $script:CanvasPadY $script:PaperW $paperH $script:Paper
    return
  }
  $top = [System.Drawing.Image]::FromFile($script:TopSkinPath)
  $mid = [System.Drawing.Image]::FromFile($script:MidSkinPath)
  $bottom = [System.Drawing.Image]::FromFile($script:BottomSkinPath)
  try {
    $x = $script:PaperX
    $y = $script:CanvasPadY
    $g.DrawImage($top, $x, $y, $script:PaperW, $top.Height)
    $cursor = $y + $top.Height
    $bottomY = $y + $paperH - $bottom.Height
    while ($cursor -lt $bottomY) {
      $h = [Math]::Min($mid.Height, $bottomY - $cursor)
      $dest = [System.Drawing.Rectangle]::new($x, $cursor, $script:PaperW, $h)
      $g.DrawImage($mid, $dest, 0, 0, $mid.Width, $h, [System.Drawing.GraphicsUnit]::Pixel)
      $cursor += $h
    }
    $g.DrawImage($bottom, $x, $bottomY, $script:PaperW, $bottom.Height)
  } finally {
    $top.Dispose()
    $mid.Dispose()
    $bottom.Dispose()
  }
}

function Title-Lines([string]$title) {
  $words = $title.Split(" ", [System.StringSplitOptions]::RemoveEmptyEntries)
  if ($words.Length -le 2) { return @($title, "") }
  if ($words.Length -eq 3) { return @($words[0], ($words[1..2] -join " ")) }
  $mid = [Math]::Ceiling($words.Length / 2)
  return @(($words[0..($mid-1)] -join " "), ($words[$mid..($words.Length-1)] -join " "))
}

function Dim-Value([string]$name) {
  if (($json.persona.PSObject.Properties.Name -contains "dimensions") -and ($json.persona.dimensions.PSObject.Properties.Name -contains $name)) {
    return [int]$json.persona.dimensions.$name
  }
  return 0
}

function Draw-PixelLine($g, [int]$x1, [int]$y1, [int]$x2, [int]$y2, [string]$color = "#111111", [int]$w = 1) {
  $pen = [System.Drawing.Pen]::new((Color-Hex $color), $w)
  $g.DrawLine($pen, $x1, $y1, $x2, $y2)
  $pen.Dispose()
}

function Draw-Dither($g, [int]$x, [int]$y, [int]$w, [int]$h, [int]$step = 4) {
  $brush = [System.Drawing.SolidBrush]::new((Color-Hex $script:Ink))
  for ($yy = $y; $yy -lt ($y + $h); $yy += $step) {
    for ($xx = $x; $xx -lt ($x + $w); $xx += $step) {
      if (((($xx + $yy) / $step) % 2) -eq 0) {
        $g.FillRectangle($brush, $xx, $yy, 1, 1)
      }
    }
  }
  $brush.Dispose()
}

function Draw-ProceduralPixelScene([string]$path, [bool]$transparent = $false) {
  $pair = New-Bitmap 640 880 $transparent
  $bmp = $pair[0]
  $g = $pair[1]
  if ($transparent) { $g.Clear([System.Drawing.Color]::Transparent) } else { $g.Clear((Color-Hex $script:Paper)) }
  $scale = 2
  $g.ScaleTransform($scale, $scale)
  if (-not $transparent) { Fill-Rect $g 0 0 320 440 $script:Paper }
  if (-not $transparent) { Stroke-Rect $g 10 10 300 420 $script:Ink 2 }
  Draw-PixelLine $g 20 72 300 72
  Draw-PixelLine $g 36 350 286 350
  Stroke-Rect $g 40 100 96 72 $script:Ink 2
  Stroke-Rect $g 168 86 104 92 $script:Ink 2
  Draw-PixelLine $g 178 112 260 112
  Draw-PixelLine $g 178 134 254 134
  Draw-PixelLine $g 178 154 236 154
  Stroke-Rect $g 122 216 142 72 $script:Ink 2
  Draw-PixelLine $g 132 232 252 232
  Draw-PixelLine $g 138 250 240 250
  Draw-PixelLine $g 144 268 254 268
  Draw-Dither $g 46 106 86 60 4
  Draw-Dither $g 126 222 134 58 4
  Stroke-Rect $g 128 124 34 50 $script:Ink 2
  Fill-Rect $g 136 138 18 19 $script:Ink
  Draw-PixelLine $g 146 174 146 214
  Draw-PixelLine $g 146 214 118 270
  Draw-PixelLine $g 146 214 184 270
  Draw-PixelLine $g 134 188 102 228
  Draw-PixelLine $g 158 188 204 228
  if ((Dim-Value "EXPLORATION") -ge 70) {
    Stroke-Rect $g 44 222 72 54 $script:Ink 2
    Draw-PixelLine $g 52 266 108 228
    Draw-PixelLine $g 66 230 102 260
  }
  if ((Dim-Value "AUTOMATION") -ge 70) {
    Stroke-Rect $g 232 206 50 82 $script:Ink 2
    for ($i = 0; $i -lt 7; $i++) { Draw-PixelLine $g 240 (218 + $i*9) 274 (218 + $i*9) }
    Draw-PixelLine $g 256 288 256 330 $script:Blue 2
  }
  if ((Dim-Value "VERIFICATION") -ge 60) {
    Stroke-Rect $g 210 318 62 36 $script:Ink 2
    Draw-PixelLine $g 220 334 234 348 $script:Blue 2
    Draw-PixelLine $g 234 348 264 322 $script:Blue 2
  }
  for ($i = 0; $i -lt 72; $i++) {
    $x = 18 + (($i * 37) % 284)
    $y = 24 + (($i * 53) % 384)
    Fill-Rect $g $x $y 1 1 $script:Ink
  }
  Save-Png $bmp $g $path
}

function Process-ExternalIllustration([string]$inputPath, [string]$outputPath) {
  $src = [System.Drawing.Image]::FromFile($inputPath)
  try {
    $prep = [System.Drawing.Bitmap]::new(512, 512)
    $pg = [System.Drawing.Graphics]::FromImage($prep)
    $pg.Clear((Color-Hex $script:Paper))
    $pg.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $prepScale = [Math]::Min(512 / $src.Width, 512 / $src.Height)
    $prepW = [int]($src.Width * $prepScale)
    $prepH = [int]($src.Height * $prepScale)
    $prepX = [int]((512 - $prepW) / 2)
    $prepY = [int]((512 - $prepH) / 2)
    $pg.DrawImage($src, $prepX, $prepY, $prepW, $prepH)
    $pg.Dispose()
    $minX = 511; $minY = 511; $maxX = 0; $maxY = 0
    for ($yy = 0; $yy -lt $prep.Height; $yy++) {
      for ($xx = 0; $xx -lt $prep.Width; $xx++) {
        $pc = $prep.GetPixel($xx, $yy)
        $pluma = [int](0.299*$pc.R + 0.587*$pc.G + 0.114*$pc.B)
        $pblue = ($pc.B -gt ($pc.R + 22) -and $pc.B -gt ($pc.G + 6))
        if (($pluma -lt 242) -or $pblue) {
          if ($xx -lt $minX) { $minX = $xx }
          if ($yy -lt $minY) { $minY = $yy }
          if ($xx -gt $maxX) { $maxX = $xx }
          if ($yy -gt $maxY) { $maxY = $yy }
        }
      }
    }
    if (($maxX -le $minX) -or ($maxY -le $minY)) {
      $minX = 0; $minY = 0; $maxX = 511; $maxY = 511
    }
    $pad = 16
    $minX = [Math]::Max(0, $minX - $pad)
    $minY = [Math]::Max(0, $minY - $pad)
    $maxX = [Math]::Min(511, $maxX + $pad)
    $maxY = [Math]::Min(511, $maxY + $pad)
    $crop = [System.Drawing.Rectangle]::new($minX, $minY, ($maxX - $minX + 1), ($maxY - $minY + 1))
    $low = [System.Drawing.Bitmap]::new(320, 440, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $lg = [System.Drawing.Graphics]::FromImage($low)
    $lg.Clear((Color-Hex $script:Paper))
    $lg.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::NearestNeighbor
    $scale = [Math]::Min(310 / $crop.Width, 430 / $crop.Height)
    $dw = [int]($crop.Width * $scale)
    $dh = [int]($crop.Height * $scale)
    $dx = [int]((320 - $dw) / 2)
    $dy = [int]((440 - $dh) / 2)
    $lg.DrawImage($prep, [System.Drawing.Rectangle]::new($dx, $dy, $dw, $dh), $crop, [System.Drawing.GraphicsUnit]::Pixel)
    $lg.Dispose()
    for ($y = 0; $y -lt $low.Height; $y++) {
      for ($x = 0; $x -lt $low.Width; $x++) {
        $c = $low.GetPixel($x, $y)
        $luma = [int](0.299*$c.R + 0.587*$c.G + 0.114*$c.B)
        if ($luma -lt 122) {
          $low.SetPixel($x, $y, (Color-Hex $script:Ink))
        } elseif ($c.B -gt ($c.R + 24) -and $c.B -gt ($c.G + 8)) {
          $low.SetPixel($x, $y, (Color-Hex $script:Blue))
        } else {
          $low.SetPixel($x, $y, [System.Drawing.Color]::Transparent)
        }
      }
    }
    $out = [System.Drawing.Bitmap]::new(640, 880, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $og = [System.Drawing.Graphics]::FromImage($out)
    $og.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::NearestNeighbor
    $og.Clear([System.Drawing.Color]::Transparent)
    $og.DrawImage($low, 0, 0, 640, 880)
    $og.Dispose()
    $out.Save($outputPath, [System.Drawing.Imaging.ImageFormat]::Png)
    $out.Dispose()
    $low.Dispose()
    $prep.Dispose()
  } finally {
    $src.Dispose()
  }
}

function Build-PersonaIllustrations() {
  $raw = Join-Path $OutputDir "persona-illustration-raw.png"
  $processed = Join-Path $OutputDir "persona-illustration-processed.png"
  if ($script:IllustrationPath) {
    Copy-Item -LiteralPath $script:IllustrationPath -Destination $raw -Force
    Process-ExternalIllustration $script:IllustrationPath $processed
  } else {
    Draw-ProceduralPixelScene $raw $false
    Draw-ProceduralPixelScene $processed $true
  }
  Copy-Item -LiteralPath $processed -Destination (Join-Path $OutputDir "character.png") -Force
  Draw-ProceduralPixelScene (Join-Path $OutputDir "character-transparent.png") $true
}

function Draw-ProcessedIllustration($g, [float]$x, [float]$y, [float]$w, [float]$h) {
  $path = Join-Path $OutputDir "persona-illustration-processed.png"
  $img = [System.Drawing.Image]::FromFile($path)
  try {
    $scale = [Math]::Min($w / $img.Width, $h / $img.Height)
    $dw = [float]($img.Width * $scale)
    $dh = [float]($img.Height * $scale)
    $dx = [float]($x + (($w - $dw) / 2))
    $dy = [float]($y + (($h - $dh) / 2))
    $g.DrawImage($img, $dx, $dy, $dw, $dh)
  } finally {
    $img.Dispose()
  }
}

function Draw-OutputTicket($g, [float]$x, [float]$y) {
  Stroke-Rect $g $x $y 190 78 $script:Red 3
  Draw-Centered $g "OUTPUT TIME" ($x + 8) ($y + 10) 174 18 $script:Red "Bold"
  Draw-DotRule $g ($x + 27) ($y + 36) 136
  Draw-Centered $g ([string]$json.generated_at_local) ($x + 8) ($y + 50) 174 15 $script:Red "Bold"
}

function Compute-Layout() {
  $rows = @($json.categories.PSObject.Properties).Count
  $activityRows = [Math]::Min(6, [Math]::Max(3, $rows))
  $base = 2540 + ([Math]::Max(0, $activityRows - 6) * 22)
  return [ordered]@{
    activityRows = $activityRows
    paperHeight = [Math]::Max(2540, $base)
  }
}

function Draw-Receipt([string]$path, [bool]$full = $false) {
  $layout = Compute-Layout
  $paperH = [int]$layout.paperHeight
  if ($full) { $paperH = [Math]::Max($paperH, 3020) }
  $canvasH = $paperH + ($script:CanvasPadY * 2)
  $pair = New-Bitmap $script:CanvasW $canvasH
  $bmp = $pair[0]
  $g = $pair[1]
  $g.Clear((Color-Hex $script:Black))
  Draw-SkinPaper $g $paperH
  $px = $script:PaperX
  $py = $script:CanvasPadY
  $pw = $script:PaperW
  $clip = [System.Drawing.RectangleF]::new(($px + 18), ($py + 14), ($pw - 36), ($paperH - 28))
  $g.SetClip($clip)
  $x0 = $px + 40
  Draw-Centered $g "CODEX RECEIPT" $px ($py + 42) $pw 44 $script:Ink "Bold"
  Draw-Centered $g "LOCAL RECORD" $px ($py + 105) $pw 18
  Draw-Centered $g "NOT OFFICIAL BILLING" $px ($py + 128) $pw 18
  Draw-DotRule $g ($px + 54) ($py + 172) ($pw - 108)
  Draw-Centered $g "WORKING PERSONA SPECIMEN" $px ($py + 218) $pw 19 $script:Ink "Regular"
  $titleLines = Title-Lines ([string]$json.persona.title)
  Draw-Centered $g $titleLines[0] ($px + 20) ($py + 258) ($pw - 40) 39 $script:Ink "Bold"
  Draw-Centered $g $titleLines[1] ($px + 20) ($py + 304) ($pw - 40) 39 $script:Ink "Bold"
  Draw-Centered $g ([string]$json.persona.secondary) $px ($py + 354) $pw 21
  Draw-Text $g "ORDER: $($json.receipt.order)" $x0 ($py + 438) 18
  Draw-Text $g "PERIOD: $($json.period)" $x0 ($py + 468) 18
  Draw-Text $g "OUTPUT TIME:" $x0 ($py + 498) 18
  Draw-OutputTicket $g ($px + 318) ($py + 446)
  Draw-DotRule $g $x0 ($py + 552) ($pw - 80)
  $y = $py + 594
  Dotted-Row $g "THREADS" ([string]$json.statistics.threads) $x0 $y ($pw - 80) 19; $y += 28
  Dotted-Row $g "TURNS" ([string]$json.statistics.turns) $x0 $y ($pw - 80) 19; $y += 28
  Dotted-Row $g "TOOLS" ([string]$json.statistics.tool_calls) $x0 $y ($pw - 80) 19; $y += 28
  Dotted-Row $g "COMMANDS" ([string]$json.statistics.command_runs) $x0 $y ($pw - 80) 19; $y += 28
  Dotted-Row $g "TOKEN" ([string]$json.statistics.tokens_total) $x0 $y ($pw - 80) 19; $y += 28
  Dotted-Row $g "COVERAGE" ("$($json.statistics.coverage_score)%") $x0 $y ($pw - 80) 19
  $y += 28
  $illusTop = $y + 34
  $illusH = if ($full) { 900 } else { 720 }
  Draw-ProcessedIllustration $g ($px + 42) $illusTop ($pw - 84) $illusH
  $y = $illusTop + $illusH + 36
  Draw-DotRule $g $x0 $y ($pw - 80); $y += 34
  Draw-Text $g "CORE CAPABILITIES" $x0 $y 22 $script:Ink "Bold"; $y += 36
  foreach ($name in @("EXPLORATION","EXECUTION","AUTOMATION","ENDURANCE","ITERATION","SYSTEMS","CONTROL","VERIFICATION")) {
    Dotted-Row $g $name ("$(Dim-Value $name)%") $x0 $y ($pw - 80) 16
    $y += 22
  }
  Draw-DotRule $g $x0 ($y + 8) ($pw - 80); $y += 36
  Draw-Text $g "TOP ACTIVITY SIGNALS" $x0 $y 22 $script:Ink "Bold"; $y += 34
  Dotted-Row $g "COMMAND RUNS" ([string]$json.statistics.command_runs) $x0 $y ($pw - 80) 16; $y += 22
  Dotted-Row $g "TOOL CALLS" ([string]$json.statistics.tool_calls) $x0 $y ($pw - 80) 16; $y += 22
  $used = 0
  foreach ($prop in ($json.categories.PSObject.Properties | Select-Object -First $layout.activityRows)) {
    Dotted-Row $g ($prop.Name.ToUpper()) ([string]$prop.Value) $x0 $y ($pw - 80) 15
    $y += 21
    $used += 1
  }
  Draw-DotRule $g $x0 ($y + 8) ($pw - 80); $y += 36
  Draw-Text $g "RECORD DETAILS" $x0 $y 22 $script:Ink "Bold"; $y += 34
  Dotted-Row $g "SOURCE" ([string]$json.statistics.source_grade) $x0 $y ($pw - 80) 15; $y += 20
  Dotted-Row $g "PUBLIC SAFE" "YES" $x0 $y ($pw - 80) 15; $y += 20
  Dotted-Row $g "CONFIDENCE" ([string]$json.persona.confidence) $x0 $y ($pw - 80) 15; $y += 20
  Dotted-Row $g "OUTPUT TIME" ([string]$json.generated_at_local) $x0 $y ($pw - 80) 15; $y += 26
  Draw-Text $g "NOTE: All identifiers are local to this record." $x0 $y 14; $y += 19
  Draw-Text $g "No external transmission. No personal data." $x0 $y 14; $y += 35
  Dotted-Row $g "TOTAL" "LOCAL RECORD" $x0 $y ($pw - 80) 22; $y += 44
  Draw-Barcode $g $x0 $y ($pw - 80) 68 ([string]$json.receipt.order); $y += 88
  Draw-Centered $g "*** DUPLICATE COPY ***" $px $y $pw 22 $script:Ink "Bold"; $y += 29
  Draw-Centered $g "KEEP FOR YOUR RECORDS" $px $y $pw 16; $y += 22
  Draw-Centered $g "All records are local to Codex." $px $y $pw 15; $y += 20
  Draw-Centered $g "Share only with trust." $px $y $pw 15
  Save-Png $bmp $g $path
}

function Write-VisualCheckReport([int]$shareW, [int]$shareH) {
  $skinExists = (Test-Path -LiteralPath $script:TopSkinPath) -and (Test-Path -LiteralPath $script:MidSkinPath) -and (Test-Path -LiteralPath $script:BottomSkinPath)
  $skinManifestPath = Join-Path $script:AssetDir "receipt-skin-manifest.json"
  $skinManifest = $null
  if (Test-Path -LiteralPath $skinManifestPath) {
    try {
      $skinManifest = Get-Content -Raw -Encoding UTF8 $skinManifestPath | ConvertFrom-Json
    } catch {
      $skinManifest = $null
    }
  }
  $report = [ordered]@{
    schema = "codex-receipt.visual-check.v3"
    deterministic_full_receipt = $true
    receipt_contract = "receipt-skin-9slice-v1"
    illustration_contract = "ai-pixel-persona-v3"
    background_strategy = "nine_slice_template_skin"
    share_size = "$($shareW)x$($shareH)"
    full_receipt_image_generation = $false
    original_reference_images_embedded = $false
    template_skin_assets_present = $skinExists
    skin_manifest_raw_reference_images_embedded = if ($skinManifest -and ($skinManifest.PSObject.Properties.Name -contains "raw_reference_images_embedded")) { [bool]$skinManifest.raw_reference_images_embedded } else { $null }
    skin_manifest_content_removed = if ($skinManifest -and ($skinManifest.PSObject.Properties.Name -contains "content_removed")) { [bool]$skinManifest.content_removed } else { $null }
    skin_manifest_interior_source_pixels_kept = if ($skinManifest -and ($skinManifest.PSObject.Properties.Name -contains "interior_source_pixels_kept")) { [bool]$skinManifest.interior_source_pixels_kept } else { $null }
    checks = [ordered]@{
      receipt_share_final_exists = (Test-Path -LiteralPath (Join-Path $OutputDir "receipt-share-final.png"))
      receipt_share_exists = (Test-Path -LiteralPath (Join-Path $OutputDir "receipt-share.png"))
      persona_illustration_processed_exists = (Test-Path -LiteralPath (Join-Path $OutputDir "persona-illustration-processed.png"))
      output_time_source = [string]$json.generated_at_local
      public_disclaimer = "LOCAL RECORD / PERSONAL SUMMARY / NOT OFFICIAL BILLING"
    }
  }
  $report | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $OutputDir "visual-check-report.json")
}

Build-PersonaIllustrations
$sharePath = Join-Path $OutputDir "receipt-share-final.png"
Draw-Receipt $sharePath $false
Copy-Item -LiteralPath $sharePath -Destination (Join-Path $OutputDir "receipt-share.png") -Force
Draw-Receipt (Join-Path $OutputDir "receipt-full-01.png") $true
$shareImg = [System.Drawing.Image]::FromFile($sharePath)
try {
  Write-VisualCheckReport $shareImg.Width $shareImg.Height
} finally {
  $shareImg.Dispose()
}
