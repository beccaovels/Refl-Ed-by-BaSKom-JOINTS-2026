import { createContext, useContext } from 'react';

export const Context = createContext(null);

export const useApp = () => useContext(Context);
