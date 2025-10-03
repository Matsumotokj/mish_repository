document.addEventListener('DOMContentLoaded', function() {
    // ----------------------------------------------------------------
    // 1. 要素の取得とデータの初期化
    // ----------------------------------------------------------------
    const phrasesDisplayContainer = document.getElementById('phrases-display-container');
    const startMessage = document.getElementById('start-message');       // ★追加 
    const userInputFormContainer = document.getElementById('user-input-form-container'); // ★追加 
    // HTMLのdata-phrases-json属性からJSON文字列を取得し、JavaScriptオブジェクトにパース
    const phrasesData = JSON.parse(phrasesDisplayContainer.dataset.phrasesJson);
    
    let currentPhraseIndex = 0; // 現在表示しているフレーズのインデックスを管理する変数

    const mainAudioPlayer = document.getElementById('main-audio-player'); // ★追加: オーディオプレーヤーの取得
    const userInputArea = document.getElementById('user-input');     // ★追加 (HTMLに存在すると仮定)
    const submitButton = document.getElementById('submit-button');       // ★追加 (HTMLに存在すると仮定)
    const playbackMode = phrasesDisplayContainer.dataset.playbackMode;
    const manualNextInstruction = document.getElementById('manual-next-instruction');

    // ★新規追加: 音声再生速度のデフォルト設定
    const DEFAULT_PLAYBACK_RATE = 1.0; // 1.0 = 標準速度, 0.8 = 80%, 1.2 = 120%
    mainAudioPlayer.playbackRate = DEFAULT_PLAYBACK_RATE; // ここで設定を適用

    // ★追加: 全てのフレーズの再生が完了したかを示すフラグ
    let isAllAudioPlayed = false;
    let isPracticeStarted  = false;
    let audioHasEnded = true;


    let isCanplayListenerRegistered = false;

    // ----------------------------------------------------------------
    // 2. 現在のフレーズを表示する関数
    // ----------------------------------------------------------------
    function displayCurrentPhrase() {
        // コンテナ内の既存のテキストを全て削除し、新しいフレーズを表示する準備
        phrasesDisplayContainer.innerHTML = ''; 

        // すべてのフレーズを表示し終えたかチェック
        if (currentPhraseIndex >= phrasesData.length) {
            // 全てのフレーズが表示し終わったら、完了メッセージを表示して処理を終了
            phrasesDisplayContainer.textContent = "全てのフレーズが表示されました。";
            console.log("全てのフレーズが完了しました。");
            isAllAudioPlayed = true; // フラグを立てる

      

            if(submitButton){
                submitButton.style.display = 'block';
            }

            manualNextInstruction.classList.remove('visible');

            return; // ここで関数を終了
        }

        // currentPhraseIndex に基づいて、現在のフレーズデータを取得
        const currentPhraseData = phrasesData[currentPhraseIndex];
        
        // 取得したフレーズのテキストをそのままコンテナに表示
        // この段階ではまだ1文字ずつの<span>要素にはしません
        phrasesDisplayContainer.textContent = currentPhraseData.text;

        manualNextInstruction.classList.remove('visible');

        if(currentPhraseData.audio_url){
            mainAudioPlayer.src = currentPhraseData.audio_url;
            mainAudioPlayer.load()
            // mainAudioPlayer.play()
            // ★変更: 練習開始後であれば音声を再生する
            // if (isPracticeStarted) {
            //     mainAudioPlayer.play();
            //     mainAudioPlayer.style.display = 'block'; // 音声プレーヤーを表示
            //     console.log(`音声再生開始: ${currentPhraseData.audio_url} (速度: ${mainAudioPlayer.playbackRate})`);
            // } else {
            //      mainAudioPlayer.style.display = 'none'; // 練習開始前は非表示のまま
            // }
            if (!isCanplayListenerRegistered) {
                mainAudioPlayer.addEventListener('canplay', handleAudioCanplay);
                isCanplayListenerRegistered = true;
            }
        }else {
            console.warn(`フレーズ ${currentPhraseIndex + 1} に音声URLがありません。`);
        }

        // デバッグ用: コンソールにも現在表示中のフレーズを出力
        console.log(`フレーズ ${currentPhraseIndex + 1} を表示: "${currentPhraseData.text}"`);
    }





    // ----------------------------------------------------------------
    // 5. 音声プレーヤー終了時のイベントリスナー (★新規追加/メインの変更)
    // ----------------------------------------------------------------
    mainAudioPlayer.addEventListener('ended', () => {
         
        // ★★★ ここから追加/変更 ★★★
        // 全ての音声再生が完了していない場合のみ、次のフレーズへ自動的に進む

        // 自動再生
        if (playbackMode==='auto' && !isAllAudioPlayed && isPracticeStarted) {
            currentPhraseIndex++; // 次のフレーズのインデックスに更新
            displayCurrentPhrase(); // 新しいフレーズを表示し、音声を再生
        }else{
            // 手動再生
            // 手動モードの場合は音声が終了したことを記録
            audioHasEnded = true;
            if (playbackMode === 'manual' && !isAllAudioPlayed) {
                manualNextInstruction.classList.add('visible'); // ★追加：手動モードで音声終了時に案内を表示
            }
        }
        // ★★★ ここまで追加/変更 ★★★
    });

    // ----------------------------------------------------------------
    // 6. 練習開始処理をまとめた関数 (★変更あり)
    // ----------------------------------------------------------------
   
    function startPractice() {
        if (isPracticeStarted) return; // 既に開始済みなら何もしない

        isPracticeStarted = true; // 練習開始フラグを立てる
        if (startMessage) startMessage.style.display = 'none'; // スタートメッセージを非表示にする
        if (phrasesDisplayContainer) phrasesDisplayContainer.style.display = 'block'; // フレーズ表示コンテナを表示する
        if (userInputFormContainer) userInputFormContainer.style.display = 'block'; // 入力フォームを表示する
        if (mainAudioPlayer) mainAudioPlayer.style.display = 'block'; // 音声プレーヤーを表示する
        
        displayCurrentPhrase(); // 最初のフレーズのテキストと音声を再生

        console.log("userInputArea:",userInputArea);
        if (userInputArea){
            userInputArea.focus(); // 練習開始と同時に入力欄にフォーカスを当てる
        }
        
        // 初回スタート時のキーイベントリスナーは不要になるので削除
        document.removeEventListener('keydown', handleStartKey);
    }

    // ----------------------------------------------------------------
    // 7. 初回再生をキー入力で開始するためのイベントリスナー
    // ----------------------------------------------------------------
    function handleStartKey(event) {
        // if (((event.ctrlKey || event.metaKey) && event.code === 'Enter') && !isPracticeStarted) {
        if ((event.code === 'Space' || event.code === 'Enter') && !isPracticeStarted) {
            event.preventDefault(); 
            console.log("練習をキー入力で開始します。");
            startPractice(); // 練習開始処理を呼び出す
        }
    }
    document.addEventListener('keydown', handleStartKey);
    document.addEventListener('keydown', handleManualNext);

    function handleAudioCanplay() {
        // ★ canplayイベントハンドラ内で、isPracticeStarted が true の場合のみ再生を開始する
        if (isPracticeStarted) {
            mainAudioPlayer.playbackRate = DEFAULT_PLAYBACK_RATE; // ここでも再設定して確実に適用
            console.log("mainAudioPlayer.playbackRate:",mainAudioPlayer.playbackRate);
            mainAudioPlayer.play().catch(error => {
                console.error("音声の自動再生がブロックされました:", error);
                // ユーザーに手動再生を促すUIを検討
            });
            console.log(`canplayイベント発生。音声再生開始 (速度: ${mainAudioPlayer.playbackRate})`);
        }
        // イベントリスナーは一度登録したら、srcが変わるたびに発生するので、ここで削除する必要はない。
        // ただし、速度変更ロジックと絡めるなら、一度削除して再登録する方が安全な場合もある。
        // 現状は displayCurrentPhrase 内で canplay リスナーが重複登録されないように制御しているのでOK。
    }

    

    function handleManualNext(event) {
        console.log("playbackMode:",playbackMode);
        console.log("event.code:",event.code);
        console.log("isPracticeStarted:",isPracticeStarted);
        console.log("!isAllAudioPlayed:",!isAllAudioPlayed);
        console.log("audioHasEnded:",audioHasEnded);

        const isCtrlPressed = event.ctrlKey || event.metaKey;

        // 手動モード、練習中、全音声未再生、かつ現在の音声が終了している場合のみ
        if (playbackMode === 'manual' && event.code === 'Enter' && isCtrlPressed && isPracticeStarted && !isAllAudioPlayed && audioHasEnded) {
            // event.preventDefault();
            // // 入力欄にフォーカスがあるときにエンターキーを押すと改行されてしまうのを防ぐ
            // if (document.activeElement === userInputArea) {
            //     userInputArea.blur(); // 一時的にフォーカスを外す
            //     setTimeout(() => userInputArea.focus(), 10); // すぐに戻す
            // }

            console.log("次に行こうとしている。");
            
            currentPhraseIndex++;
            displayCurrentPhrase();
        }
    }
    
    // ----------------------------------------------------------------
    // (補足) 今回はまだ使用しない要素
    // ----------------------------------------------------------------
    // これらは今後追加する機能で使うので、今は気にしなくてOK
    // const mainAudioPlayer = document.getElementById('main-audio-player');
    // const userInputArea = document.getElementById('user-input-area'); 
    // const submitButton = document.getElementById('submit-button');
    // const toggleCheckbox = document.getElementById('toggle-text-visibility');
});
