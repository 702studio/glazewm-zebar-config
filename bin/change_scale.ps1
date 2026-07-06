param(
    [string]$Direction
)

$output = & "C:\Users\tolgaozisik\bin\SetDpi.exe" get
if ($output -match "(\d+)") {
    $current = [int]$Matches[1]
} else {
    $current = 100
}

$scales = @(100, 125, 150, 175, 200)
$index = $scales.IndexOf($current)

if ($index -lt 0) {
    $closestIndex = 0
    $minDiff = [int]::MaxValue
    for ($i = 0; $i -lt $scales.Count; $i++) {
        $diff = [Math]::Abs($scales[$i] - $current)
        if ($diff -lt $minDiff) {
            $minDiff = $diff
            $closestIndex = $i
        }
    }
    $index = $closestIndex
}

if ($Direction -eq "up") {
    if ($index -lt ($scales.Count - 1)) {
        $newScale = $scales[$index + 1]
    } else {
        $newScale = $scales[$index]
    }
} elseif ($Direction -eq "down") {
    if ($index -gt 0) {
        $newScale = $scales[$index - 1]
    } else {
        $newScale = $scales[$index]
    }
}

if ($newScale) {
    & "C:\Users\tolgaozisik\bin\SetDpi.exe" $newScale
}
