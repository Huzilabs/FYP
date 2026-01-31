$ID = 'd086480d-7cf9-4d06-a5ab-e8c4a8118214'
$BASE = 'http://127.0.0.1:5000'
$headers = @{ 'X-User-Id' = $ID }

function Print($label, $obj) {
  Write-Output "--- $label ---"
  if ($null -eq $obj) { Write-Output 'NULL' ; return }
  try { Write-Output ($obj | ConvertTo-Json -Depth 6) } catch { Write-Output $obj }
}

# 1) List templates
try {
  $list = Invoke-RestMethod -Uri "$BASE/api/workouts/templates" -Method Get -Headers $headers -TimeoutSec 30
  Print 'LIST TEMPLATES' $list
} catch {
  Print 'LIST ERROR' $_.Exception.Message
}

# 2) Create a private template named 'push'
$body = @{ name = 'push'; default_count = 10; default_duration_minutes = 5; editable_by_user = $true } | ConvertTo-Json
try {
  $create = Invoke-RestMethod -Uri "$BASE/api/users/$ID/workout_templates" -Method Post -Headers $headers -Body $body -ContentType 'application/json' -TimeoutSec 30
  Print 'CREATE' $create
  $tid = $create.template.id
} catch {
  Print 'CREATE ERROR' $_.Exception.Message
  $tid = $null
}

# 3) List user's merged workouts
try {
  $merged = Invoke-RestMethod -Uri "$BASE/api/users/$ID/workouts" -Method Get -TimeoutSec 30
  Print 'MERGED WORKOUTS' $merged
} catch {
  Print 'MERGED ERROR' $_.Exception.Message
}

# 4) Update user's workout values for the new template (if created)
if ($tid) {
  $patchBody = @{ count = 25; duration_minutes = 7 } | ConvertTo-Json
  try {
    $upd = Invoke-RestMethod -Uri "$BASE/api/users/$ID/workouts/$tid" -Method Patch -Headers $headers -Body $patchBody -ContentType 'application/json' -TimeoutSec 30
    Print 'PATCH USER WORKOUT' $upd
  } catch {
    Print 'PATCH ERROR' $_.Exception.Message
  }

  # 5) Fetch history for that template
  try {
    $hist = Invoke-RestMethod -Uri "$BASE/api/users/$ID/workouts/$tid/history" -Method Get -Headers $headers -TimeoutSec 30
    Print 'HISTORY' $hist
  } catch {
    Print 'HISTORY ERROR' $_.Exception.Message
  }

  # 6) Delete the created template
  try {
    $del = Invoke-RestMethod -Uri "$BASE/api/workout_templates/$tid" -Method Delete -Headers $headers -TimeoutSec 30
    Print 'DELETE' $del
  } catch {
    Print 'DELETE ERROR' $_.Exception.Message
  }
}

# 7) Final list templates
try {
  $final = Invoke-RestMethod -Uri "$BASE/api/workouts/templates" -Method Get -Headers $headers -TimeoutSec 30
  Print 'FINAL LIST' $final
} catch {
  Print 'FINAL LIST ERROR' $_.Exception.Message
}
