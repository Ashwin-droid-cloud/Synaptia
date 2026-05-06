/**
 * firebase-config.js — Synaptia Firebase Client-Side SDK
 * Project: synaptia-4c06c
 *
 * Initializes Firebase App, Firestore, Auth (Google), and Analytics.
 * Exports `db`, `auth`, and helper functions consumed by script.js.
 *
 * Served statically by Flask — no Firebase Hosting required.
 * Compatible with Firebase JS SDK v10 (modular/ESM via CDN).
 */

import { initializeApp }                         from 'https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js';
import { getFirestore, doc, setDoc, getDoc,
         collection, addDoc, serverTimestamp }   from 'https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js';
import { getAuth, GoogleAuthProvider,
         signInWithPopup, signOut,
         onAuthStateChanged,
         signInWithEmailAndPassword,
         createUserWithEmailAndPassword }         from 'https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js';
import { getAnalytics, logEvent }                from 'https://www.gstatic.com/firebasejs/10.12.2/firebase-analytics.js';

/* ─────────────────────────────────────────────
   Firebase Configuration
   (Public config — security enforced via
   Firestore Security Rules in the Console)
───────────────────────────────────────────── */
const firebaseConfig = {
  apiKey:            'AIzaSyBZYDhMURi5LhOsvqkM4WxrDP4DxzU8nFU',
  authDomain:        'synaptia-4c06c.firebaseapp.com',
  projectId:         'synaptia-4c06c',
  storageBucket:     'synaptia-4c06c.firebasestorage.app',
  messagingSenderId: '621450912800',
  appId:             '1:621450912800:web:dbda19136df63d4f32c845',
  measurementId:     'G-D3M3EGH0NE',
};

/* ─────────────────────────────────────────────
   Initialize Firebase Services
───────────────────────────────────────────── */
const app       = initializeApp(firebaseConfig);
const db        = getFirestore(app);
const auth      = getAuth(app);
const analytics = getAnalytics(app);

const googleProvider = new GoogleAuthProvider();

/* ─────────────────────────────────────────────
   Auth Helpers
───────────────────────────────────────────── */

/**
 * Sign in with a Google popup.
 * Returns the Firebase User object on success.
 */
async function signInWithGoogle() {
  try {
    const result = await signInWithPopup(auth, googleProvider);
    return result.user;
  } catch (err) {
    console.error('[Synaptia/Firebase] Google sign-in failed:', err.message);
    throw err;
  }
}

/**
 * Sign out the current user.
 */
async function firebaseSignOut() {
  try {
    await signOut(auth);
  } catch (err) {
    console.error('[Synaptia/Firebase] Sign-out failed:', err.message);
  }
}

/**
 * Listen for auth state changes.
 * @param {function} callback  Receives (user | null)
 */
function onAuthChange(callback) {
  return onAuthStateChanged(auth, callback);
}

/**
 * Sign in with email and password.
 */
async function signInEmail(email, password) {
  return signInWithEmailAndPassword(auth, email, password);
}

/**
 * Create a new account with email and password.
 */
async function signUpEmail(email, password) {
  return createUserWithEmailAndPassword(auth, email, password);
}

/* ───────────────────────────────────────────────
   Firestore Session Helpers
───────────────────────────────────────────── */

/**
 * Persist a session snapshot to Firestore.
 * Document path: sessions/{sessionId}
 *
 * @param {string} sessionId
 * @param {object} data  — score, solved, attempts, hintsUsed, etc.
 */
async function saveSession(sessionId, data) {
  try {
    const ref = doc(db, 'sessions', sessionId);
    await setDoc(ref, {
      ...data,
      updatedAt: serverTimestamp(),
    }, { merge: true });
  } catch (err) {
    console.warn('[Synaptia/Firebase] saveSession failed:', err.message);
  }
}

/**
 * Load a previously saved session from Firestore.
 * Returns the data object or null if not found.
 *
 * @param {string} sessionId
 */
async function loadSession(sessionId) {
  try {
    const ref  = doc(db, 'sessions', sessionId);
    const snap = await getDoc(ref);
    return snap.exists() ? snap.data() : null;
  } catch (err) {
    console.warn('[Synaptia/Firebase] loadSession failed:', err.message);
    return null;
  }
}

/**
 * Append a history entry to the sessions/{sessionId}/history sub-collection.
 *
 * @param {string} sessionId
 * @param {object} entry  — puzzle question, type, difficulty, solved, score, elapsed
 */
async function saveHistoryEntry(sessionId, entry) {
  try {
    const colRef = collection(db, 'sessions', sessionId, 'history');
    await addDoc(colRef, {
      ...entry,
      timestamp: serverTimestamp(),
    });
  } catch (err) {
    console.warn('[Synaptia/Firebase] saveHistoryEntry failed:', err.message);
  }
}

/* ─────────────────────────────────────────────
   Analytics Helpers
───────────────────────────────────────────── */

/**
 * Log a puzzle solve / skip event to Firebase Analytics.
 *
 * @param {string}  puzzleType   — riddle | math | logic | wordplay | trivia
 * @param {string}  difficulty   — easy | medium | hard
 * @param {boolean} solved
 * @param {number}  score
 * @param {number}  elapsed      seconds taken
 */
function logPuzzleEvent(puzzleType, difficulty, solved, score, elapsed) {
  try {
    logEvent(analytics, solved ? 'puzzle_solved' : 'puzzle_skipped', {
      puzzle_type: puzzleType,
      difficulty,
      score,
      elapsed_seconds: elapsed,
    });
  } catch (err) {
    console.warn('[Synaptia/Firebase] logPuzzleEvent failed:', err.message);
  }
}

/**
 * Log a generic named event.
 * @param {string} eventName
 * @param {object} params
 */
function logAnalyticsEvent(eventName, params = {}) {
  try {
    logEvent(analytics, eventName, params);
  } catch (err) {
    console.warn('[Synaptia/Firebase] logAnalyticsEvent failed:', err.message);
  }
}

/* ─────────────────────────────────────────────
   Firestore Test Write (runs once on load)
   Writes a doc to `_test_writes/{timestamp}`
   to confirm Firestore connectivity.
   Remove or guard behind a debug flag in production.
───────────────────────────────────────────── */
(async function firestoreTestWrite() {
  try {
    const ref = doc(db, '_test_writes', `init_${Date.now()}`);
    await setDoc(ref, {
      message:   'Synaptia Firebase connected successfully',
      timestamp: serverTimestamp(),
      userAgent: navigator.userAgent,
    });
    console.log('[Synaptia/Firebase] ✓ Firestore test write succeeded');
  } catch (err) {
    console.error('[Synaptia/Firebase] ✗ Firestore test write failed:', err.message);
  }
})();

/* ─────────────────────────────────────────────
   Exports
───────────────────────────────────────────── */
export {
  db,
  auth,
  analytics,
  // Auth
  signInWithGoogle,
  signInEmail,
  signUpEmail,
  firebaseSignOut,
  onAuthChange,
  // Firestore
  saveSession,
  loadSession,
  saveHistoryEntry,
  // Analytics
  logPuzzleEvent,
  logAnalyticsEvent,
};

console.log('[Synaptia/Firebase] SDK initialised — project: synaptia-4c06c');
