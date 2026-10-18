param([ValidateSet('listen','speak','probe')][string]$Operation, [string]$AudioPath)
$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
Add-Type -AssemblyName System.Speech
if ($Operation -ne 'listen') {
    $speaker = [System.Speech.Synthesis.SpeechSynthesizer]::new()
    try {
        if ($Operation -eq 'probe') {
            $speaker.SelectVoice('Microsoft Zira Desktop')
            $speaker.SetOutputToWaveFile($AudioPath)
            $speaker.Speak('What time is it?')
        } else {
            $speaker.Speak([Console]::In.ReadToEnd())
        }
    } finally { $speaker.Dispose() }
    if ($Operation -eq 'speak') { exit 0 }
}
$culture = [Globalization.CultureInfo]::GetCultureInfo('en-US')
$engine = [System.Speech.Recognition.SpeechRecognitionEngine]::new($culture)
try {
    $engine.LoadGrammar([System.Speech.Recognition.DictationGrammar]::new())
    if ($Operation -eq 'probe') {
        $engine.SetInputToWaveFile($AudioPath)
        $recognized = $engine.Recognize()
        if (-not $recognized) { throw 'Speech probe produced no transcript' }
        @{text=$recognized.Text; confidence=$recognized.Confidence; source='generated audio, not microphone'} | ConvertTo-Json -Compress
    } else {
        $engine.SetInputToDefaultAudioDevice()
        $engine.InitialSilenceTimeout = [TimeSpan]::FromSeconds(8)
        $engine.EndSilenceTimeout = [TimeSpan]::FromMilliseconds(850)
        $subscription = Register-ObjectEvent -InputObject $engine -EventName RecognizeCompleted -SourceIdentifier KairoSpeechComplete
        $release = [Console]::In.ReadLineAsync()
        $engine.RecognizeAsync([System.Speech.Recognition.RecognizeMode]::Single)
        $limit = [DateTime]::UtcNow.AddSeconds(20)
        $closing = $false
        try {
            while ([DateTime]::UtcNow -lt $limit) {
                if ($release.IsCompleted -and -not $closing) {
                    $engine.RecognizeAsyncStop()
                    $closing = $true
                }
                @{level=$engine.AudioLevel} | ConvertTo-Json -Compress
                $finished = Get-Event -SourceIdentifier KairoSpeechComplete -ErrorAction SilentlyContinue
                if ($finished) {
                    if ($finished.SourceEventArgs.Result) { @{text=$finished.SourceEventArgs.Result.Text} | ConvertTo-Json -Compress }
                    break
                }
                Start-Sleep -Milliseconds 50
            }
        } finally {
            $engine.RecognizeAsyncCancel()
            Unregister-Event -SourceIdentifier KairoSpeechComplete -ErrorAction SilentlyContinue
            Remove-Event -SourceIdentifier KairoSpeechComplete -ErrorAction SilentlyContinue
        }
    }
} finally { $engine.Dispose() }
