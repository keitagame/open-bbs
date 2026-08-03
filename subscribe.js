// Base64URL文字列を Uint8Array（バイナリ）に変換する関数
function urlBase64ToUint8Array(base64String) {
    // 末尾の = (パディング) を補完し、記号を置換する
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
        .replace(/\-/g, '+')
        .replace(/_/g, '/');

    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
}

async function subscribePush(bbs, key) {
    try {
        // 1. まず Service Worker を登録する
        await navigator.serviceWorker.register('https://shinte.tech/sw.js');

        // 2. Service Worker が「アクティブ（準備完了）」状態になるのを確実に待つ
        const reg = await navigator.serviceWorker.ready;

        // 3. 公開鍵を Uint8Array に変換して subscribe を実行する
        const sub = await reg.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: urlBase64ToUint8Array('BB1Y7YLU6yPzprmmpD8wM8oLIB9bhX1rWxwsvBw4FPV2HAEWWO8X7pL4jllckhhVAM5aR5-JRyFRkn4brcHD1WQ')
        });

        // 4. サーバーへ送信
        await fetch(`/test/push_sub.cgi`, {
            method: 'POST',
            body: JSON.stringify({
                bbs, key, subscription: sub
            })
        });

        alert('通知を購読しました');
        
    } catch (error) {
        console.error('購読処理中にエラーが発生しました:', error);
        alert('通知の登録に失敗しました。詳細はコンソールを確認してください。');
    }
}
