import numpy as np
import pandas as pd
from scipy.optimize import minimize

class CrypashOptimizer:
    def __init__(self, risk_profile, capital_amount):
        """
        Initializes the Optimizer.
        :param risk_profile: 'Conservative', 'Moderate', 'Aggressive'
        :param capital_amount: Float, USD capital available.
        """
        self.risk_profile = risk_profile
        self.capital = capital_amount
        
    def determine_asset_count(self):
        """
        Returns optimal number of assets (N) based on Capital and Marginal Utility of Diversification.
        """
        if self.capital < 10000:
            # Accumulation Phase: Concentrate to build wealth (5-7 assets)
            return 6 
        elif self.capital < 100000:
            # Growth Phase: Balance (8-12 assets)
            return 10
        else:
            # Preservation Phase: Diversify (12-18 assets)
            return 15

    def select_universe(self, ranking_df):
        """
        Filters and selects top candidates based on Multi-Factor Score.
        """
        # 1. Basic Filters
        df = ranking_df.copy()
        
        # Ensure we have required columns
        req_cols = ['Crypash_Score', 'Vol_30D', 'RSI']
        for c in req_cols:
            if c not in df.columns: return pd.DataFrame() # Fail safe
            
        # Filter: Liquidity & Quality
        df = df[df['Crypash_Score'] >= 60] # Grade B minimum
        
        # 2. Calculate Multi-Factor Score (Smart Beta)
        # Factor 1: Quality (Score) - Higher is better
        # Factor 2: Momentum (RSI) - 50-70 is sweet spot, but for scoring we want trend. 
        #           Let's use a simplified logical score.
        # Factor 3: Low Vol - Lower is better
        
        # Normalize columns (Simple Min-Max for scoring)
        def normalize(series):
            return (series - series.min()) / (series.max() - series.min())
        
        df['Norm_Score'] = normalize(df['Crypash_Score'])
        df['Norm_Vol'] = normalize(df['Vol_30D'])
        
        # Smart Beta Formula
        # Aggressive: Focus on Score + Momentum (ignored here for simplicity, reusing Score)
        # Conservative: Focus on Low Vol
        
        if self.risk_profile == 'Conservative':
            # 60% Low Vol, 40% Quality
            df['Factor_Score'] = (0.4 * df['Norm_Score']) - (0.6 * df['Norm_Vol'])
        elif self.risk_profile == 'Aggressive':
            # 70% Quality/Growth, 30% Vol (Risk tolerance)
            df['Factor_Score'] = (0.7 * df['Norm_Score']) - (0.3 * df['Norm_Vol'])
        else:
            # Balanced
            df['Factor_Score'] = (0.5 * df['Norm_Score']) - (0.5 * df['Norm_Vol'])
            
        # Sort
        df = df.sort_values(by='Factor_Score', ascending=False)
        
        # Select Top N
        n = self.determine_asset_count()
        
        # Apply Sector Constraint Logic (Naive: Max 2 per narrative)
        # We need 'Narrative' column.
        selected = []
        sector_counts = {}
        
        for idx, row in df.iterrows():
            if len(selected) >= n: break
            
            narrative = row.get('Narrative', 'Unknown')
            if sector_counts.get(narrative, 0) >= 2:
                continue # Skip if sector full
            
            selected.append(row)
            sector_counts[narrative] = sector_counts.get(narrative, 0) + 1
            
        return pd.DataFrame(selected)

    def optimize_weights(self, price_history_df):
        """
        Calculates optimal weights (Mean-Variance Optimization).
        """
        if price_history_df.empty: return {}
        
        # 1. Calculate Returns & Covariance
        returns = price_history_df.pct_change().dropna()
        mean_returns = returns.mean() * 365 # Annualized
        cov_matrix = returns.cov() * 365
        
        num_assets = len(price_history_df.columns)
        tickers = price_history_df.columns.tolist()
        
        # 2. Define Objective Function
        def portfolio_performance(weights, mean_returns, cov_matrix):
            p_ret = np.sum(mean_returns * weights)
            p_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            return p_ret, p_vol

        def neg_sharpe(weights, mean_returns, cov_matrix, risk_free_rate=0.0):
            p_ret, p_vol = portfolio_performance(weights, mean_returns, cov_matrix)
            return -(p_ret - risk_free_rate) / p_vol
        
        def min_volatility(weights, mean_returns, cov_matrix):
            return portfolio_performance(weights, mean_returns, cov_matrix)[1]

        # 3. Optimization Setup
        constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1}) # Sum of weights = 1
        bounds = tuple((0.03, 0.25) for asset in range(num_assets)) # Min 3%, Max 25% constraint
        
        init_guess = num_assets * [1. / num_assets,]
        
        # Choose Objective based on Profile
        if self.risk_profile == 'Conservative':
            target_fun = min_volatility
        else:
            target_fun = neg_sharpe
            
        try:
            result = minimize(target_fun, init_guess, args=(mean_returns, cov_matrix), 
                              method='SLSQP', bounds=bounds, constraints=constraints)
            
            opt_weights = result.x
        except:
            # Fallback to Equal Weight if optimization fails
            opt_weights = init_guess

        # Return Dictionary
        return {tickers[i]: round(opt_weights[i], 4) for i in range(num_assets)}
