importScripts('https://www.gstatic.com/firebasejs/9.23.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/9.23.0/firebase-messaging-compat.js');

// =====================================================================
// ATENÇÃO: APAGUE O BLOCO ABAIXO E COLE O SEU FIREBASE CONFIG REAL AQUI
// =====================================================================
const firebaseConfig = {
  apiKey: "AIzaSyCB13_Bhe2fzb059vT9mP1U-JUi5-5d7Z0",
  authDomain: "sisadam-comunica.firebaseapp.com",
  projectId: "sisadam-comunica",
  storageBucket: "sisadam-comunica.firebasestorage.app",
  messagingSenderId: "471948621207",
  appId: "1:471948621207:web:ca9d66c6ae1a94468540d2",
  measurementId: "G-GMX6ZK4182"
};
// =====================================================================

// Inicializa o Firebase no fundo do celular
firebase.initializeApp(firebaseConfig);
const messaging = firebase.messaging();

// Este código recebe a mensagem do SISADAM COMUNICA quando o celular do morador está bloqueado ou no bolso
messaging.onBackgroundMessage(function(payload) {
    const notificationTitle = payload.notification.title;
    const notificationOptions = {
        body: payload.notification.body,
        icon: 'https://cdn-icons-png.flaticon.com/512/3063/3063822.png', // Ícone de uma caixa/encomenda
        badge: 'https://cdn-icons-png.flaticon.com/512/3063/3063822.png'
    };

    self.registration.showNotification(notificationTitle, notificationOptions);
});