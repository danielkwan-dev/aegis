import { useAuth0 } from "@auth0/auth0-react";
import './App.css'

function App() {
  const { isLoading, isAuthenticated, error, user, loginWithRedirect, logout } = useAuth0();

  if (isLoading) {
    return <div>Loading Aegis Identity...</div>;
  }

  if (error) {
    return <div>Oops... {error.message}</div>;
  }

  return (
    <div className="app-container" style={{ textAlign: 'center', marginTop: '50px' }}>
      <h1>Aegis Privacy Agent</h1>

      {isAuthenticated ? (
        <div>
          <img src={user.picture} alt={user.name} style={{ borderRadius: '50%', width: '100px' }} />
          <h2>Welcome, {user.name}</h2>
          <p>{user.email}</p>
          <button onClick={() => logout({ logoutParams: { returnTo: window.location.origin } })}>
            Log Out
          </button>
        </div>
      ) : (
        <button onClick={() => loginWithRedirect()}>
          Log In to Aegis
        </button>
      )}
    </div>
  );
}

export default App;