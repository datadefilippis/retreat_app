/**
 * /spazio — l'indirizzo da dire a voce e da mettere nelle email
 * (25/9/2026, founder): chi e' dentro va al gestionale, chi non lo e'
 * passa dall'accesso e poi ci arriva. Nessuna pagina: solo la strada.
 */
import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function SpazioRedirect() {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return null;
  return <Navigate to={isAuthenticated ? '/dashboard' : '/accedi?next=%2Fdashboard'} replace />;
}
