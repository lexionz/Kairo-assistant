$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
Add-Type -AssemblyName System.Speech
$culture = [Globalization.CultureInfo]::GetCultureInfo('en-US')
$engine = [System.Speech.Recognition.SpeechRecognitionEngine]::new($culture)
try {
    $builder = [System.Speech.Recognition.GrammarBuilder]::new('Hey Kairo')
    $builder.Culture = [Globalization.CultureInfo]::GetCultureInfo('en-US')
    $engine.LoadGrammar([System.Speech.Recognition.Grammar]::new($builder))
    $engine.SetInputToDefaultAudioDevice()
    @{ready=$true} | ConvertTo-Json -Compress
    while ($true) {
        $result = $engine.Recognize([TimeSpan]::FromSeconds(2))
        if ($result) {
            @{text=$result.Text; confidence=$result.Confidence} | ConvertTo-Json -Compress
        }
    }
} finally { $engine.Dispose() }
