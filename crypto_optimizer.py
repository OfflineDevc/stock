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
        Selects assets using a 'Pyramid' Tiered Strategy.
        Tier 1 (Foundation): Top Trusted (Blue Chips)
        Tier 2 (Growth): High Crypash Score (Quality)
        Tier 3 (Alpha): High Momentum/Volatility (Potential)
        """
        if ranking_df.empty: return pd.DataFrame()
        
        df = ranking_df.copy()
        
        # Helper: Ensure we have data
        req_cols = ['Symbol', 'Crypash_Score', 'Vol_30D', 'RSI']
        for c in req_cols:
            if c not in df.columns: return pd.DataFrame()
            
        # --- PYRAMID SELECTION ---
        target_n = self.determine_asset_count()
        
        # 1. Foundation (Blue Chips) - Safety
        # We assume known list or top matches
        blue_chips = ['BTC-USD', 'ETH-USD', 'SOL-USD', 'BNB-USD', 'XRP-USD', 'ADA-USD', 'AVAX-USD']
        foundation_candidates = df[df['Symbol'].isin(blue_chips)].sort_values(by='Crypash_Score', ascending=False)
        
        # Select Top 3-5 Foundation
        n_foundation = max(2, int(target_n * 0.3)) # 30% count
        selected_foundation = foundation_candidates.head(n_foundation)
        
        # 2. Core Growth (Quality) - High Score
        # Exclude already selected
        remaining = df[~df['Symbol'].isin(selected_foundation['Symbol'])]
        # Sort by Score
        growth_candidates = remaining.sort_values(by='Crypash_Score', ascending=False)
        
        n_growth = max(3, int(target_n * 0.5)) # 50% count
        selected_growth = growth_candidates.head(n_growth)
        
        # 3. Alpha (Momentum) - High RSI/Vol (but check for reasonable limits)
        remaining = remaining[~remaining['Symbol'].isin(selected_growth['Symbol'])]
        # Sort by RSI (Momentum) or Vol
        alpha_candidates = remaining.sort_values(by='RSI', ascending=False)
        
        n_alpha = max(2, int(target_n * 0.2)) # 20% count
        selected_alpha = alpha_candidates.head(n_alpha)
        
        # Combine
        combined_df = pd.concat([selected_foundation, selected_growth, selected_alpha]).drop_duplicates(subset=['Symbol'])
        
        # Label Tiers
        combined_df['Tier'] = 'Growth'
        combined_df.loc[combined_df['Symbol'].isin(blue_chips), 'Tier'] = 'Foundation'
        combined_df.loc[combined_df['Symbol'].isin(selected_alpha['Symbol']), 'Tier'] = 'Alpha'
        
        return combined_df.head(target_n)

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
