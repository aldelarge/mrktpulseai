import os
from webapp import app  # Make sure this is at the top of your file
from collections import defaultdict
from polygon import StocksClient
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv
import concurrent.futures
from daily_data import (
    fetch_rsi,
    fetch_macd,
    fetch_relative_volume,
    fetch_support_resistance,
    fetch_market_snapshot
)
from webapp import create_app, db
from strategy_sentiment_map import strategy_sentiment_map


def get_prequalified_stocks(snapshot, min_price=2000, min_volume=10_000_000, min_change_pct=-2, min_market_cap=100_000_000_000, min_prev_volume=20_000_000, min_volatility=0.01):
    """
    Universal pre-screener to filter out garbage stocks before running technical analysis.
    Keeps only liquid, actively traded stocks with decent price and intraday movement.
    Suitable for all strategies: breakout, breakdown, momentum, etc.
    """
    print("filtering prequalified stocks")
    prequalified = []

    for stock in snapshot:
        try:
            symbol = stock['ticker']
            price = stock['day']['c']
            volume = stock['day']['v']
            prev_volume = stock.get('prevDay', {}).get('v', 0)
            change_pct = stock.get('todaysChangePerc', 0)
            market_cap = stock.get('market_cap')
            high = stock['day']['h']
            low = stock['day']['l']

            # 💵 Price filter
            if price < min_price:
                continue

            # 📈 Volume today and yesterday
            if volume < min_volume or prev_volume < min_prev_volume:
                continue

            # 🧭 Exclude flat/no-trade stocks
            if high - low < price * min_volatility:
                continue

            # 📉 Optional: exclude total dead stocks
            if change_pct < min_change_pct:
                continue

            # 🏢 Optional: skip tiny market caps if available
            if market_cap is not None and market_cap < min_market_cap:
                continue

            prequalified.append({
                "symbol": symbol,
                "price": price,
                "volume": volume,
                "change_pct": change_pct,
                "market_cap": market_cap
            })

        except Exception as e:
            print(f"⚠️ Skipping {stock.get('ticker', 'UNKNOWN')}: {e}")
            continue

    print(f"🔍 Prequalified {len(prequalified)} stocks.")
    # Deduplicate by symbol
    seen = set()
    deduped = []
    for stock in prequalified:
        if stock['symbol'] not in seen:
            deduped.append(stock)
            seen.add(stock['symbol'])

    print(f"🔍 Deduplicated down to {len(deduped)} stocks.")
    return prequalified

def run_technical_analysis(prequalified_stocks, max_workers=10):
    """
    Runs RSI, MACD, RVOL, and Support/Resistance on each prequalified stock using multithreading.
    Prints the results and returns a list of dictionaries with all technical data.
    """
    tech_snapshots = []

    def process_one(stock):
        try:
            symbol = stock["symbol"]
            price = stock["price"]

            rsi = fetch_rsi(symbol)
            macd, signal, histogram = fetch_macd(symbol)
            rvol = fetch_relative_volume(symbol)
            support, resistance = fetch_support_resistance(symbol)

            snapshot = {
                "symbol": symbol,
                "price": price,
                "rsi": rsi,
                "macd": macd,
                "signal": signal,
                "histogram": histogram,
                "rvol": rvol,
                "support": support,
                "resistance": resistance
            }

            # 🔍 Print technicals for visibility
            print(f"\n📊 {symbol} | Price: ${price:.2f}")
            print(f"   RSI: {rsi}, RVOL: {rvol}")
            print(f"   MACD: {macd}, Signal: {signal}, Histogram: {histogram}")
            print(f"   Support: {support}, Resistance: {resistance}")

            return snapshot

        except Exception as e:
            print(f"⚠️ Error analyzing {stock.get('symbol', 'UNKNOWN')}: {e}")
            return None

    print(f"\n⚙️ Running technical analysis on {len(prequalified_stocks)} stocks using {max_workers} threads...")

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = executor.map(process_one, prequalified_stocks)

    for result in results:
        if result:
            tech_snapshots.append(result)

    print(f"\n🧠 Completed technical analysis for {len(tech_snapshots)} stocks.")
    return tech_snapshots

def find_breakout_candidates(tech_snapshots):
    """
    Filters technical snapshots for breakout setups:
    - RSI 50–70
    - MACD bullish
    - Price near resistance
    - RVOL > 1.2
    """
    breakout_candidates = []

    for stock in tech_snapshots:
        try:
            rsi = stock["rsi"]
            macd = stock["macd"]
            signal = stock["signal"]
            histogram = stock["histogram"]
            rvol = stock["rvol"]
            resistance = stock["resistance"]
            price = stock["price"]

            near_resistance = resistance and price >= resistance * 0.95
            macd_bullish = macd and signal and (macd > signal or (histogram and histogram > 0))

            if rsi and 50 < rsi < 70 and rvol and rvol > 1.2 and near_resistance and macd_bullish:
                breakout_candidates.append(stock)

        except Exception as e:
            print(f"⚠️ Skipping {stock['symbol']}: {e}")
            continue

    print(f"🚀 Found {len(breakout_candidates)} breakout candidates.")
    return breakout_candidates

def find_breakdown_candidates(tech_snapshots):
    """
    Filters technical snapshots for breakdown setups:
    - RSI 30–50
    - MACD bearish
    - Price near support
    - RVOL > 1.2
    """
    breakdown_candidates = []

    for stock in tech_snapshots:
        try:
            rsi = stock["rsi"]
            macd = stock["macd"]
            signal = stock["signal"]
            histogram = stock["histogram"]
            rvol = stock["rvol"]
            support = stock["support"]
            price = stock["price"]

            near_support = support and price <= support * 1.05
            macd_bearish = macd and signal and (macd < signal or (histogram and histogram < 0))

            if rsi and 30 < rsi < 50 and rvol and rvol > 1.2 and near_support and macd_bearish:
                breakdown_candidates.append(stock)

        except Exception as e:
            print(f"⚠️ Skipping {stock['symbol']}: {e}")
            continue

    print(f"🩸 Found {len(breakdown_candidates)} breakdown candidates.")
    return breakdown_candidates

def find_momentum_surge_candidates(tech_snapshots):
    """
    Finds momentum candidates:
    - RSI > 70
    - RVOL > 2.0
    - MACD bullish
    - Price breaking resistance
    """
    momentum_candidates = []

    for stock in tech_snapshots:
        try:
            rsi = stock["rsi"]
            rvol = stock["rvol"]
            macd = stock["macd"]
            signal = stock["signal"]
            histogram = stock["histogram"]
            resistance = stock["resistance"]
            price = stock["price"]

            macd_bullish = macd and signal and (macd > signal or (histogram and histogram > 0))
            price_breaking_out = resistance and price > resistance

            if rsi and rsi > 70 and rvol and rvol > 2.0 and macd_bullish and price_breaking_out:
                momentum_candidates.append(stock)

        except Exception as e:
            print(f"⚠️ Skipping momentum candidate {stock.get('symbol', 'UNKNOWN')}: {e}")
            continue

    print(f"⚡ Found {len(momentum_candidates)} momentum surge candidates.")
    return momentum_candidates

def find_pullback_buy_zone_candidates(tech_snapshots):
    """
    Finds healthy pullbacks in uptrends:
    - RSI between 40–50
    - MACD still bullish
    - Price near support
    """
    pullbacks = []
    for stock in tech_snapshots:
        try:
            if 40 <= stock["rsi"] <= 50 and stock["macd"] > stock["signal"]:
                if stock["support"] and stock["price"] <= stock["support"] * 1.05:
                    pullbacks.append(stock)
        except:
            continue
    print(f"🔁 Found {len(pullbacks)} pullback buy zone candidates.")
    return pullbacks

def find_reversal_candidates(tech_snapshots):
    """
    Finds potential reversal setups:
    - MACD just crossed over signal
    - Histogram flipped direction (momentum shift)
    """
    reversals = []
    for stock in tech_snapshots:
        try:
            histogram = stock["histogram"]
            # Simplified: recent histogram just flipped from neg to pos or vice versa
            if histogram and abs(histogram) < 0.1:  # momentum flattening
                reversals.append(stock)
        except:
            continue
    print(f"🔄 Found {len(reversals)} reversal candidates.")
    return reversals

def find_overbought_fade_candidates(tech_snapshots):
    """
    Finds overbought names likely to fade:
    - RSI > 80
    - MACD bearish or flattening
    - Price extended far above resistance
    """
    fades = []
    for stock in tech_snapshots:
        try:
            extended = stock["resistance"] and stock["price"] > stock["resistance"] * 1.05
            macd_flat_or_bearish = stock["macd"] < stock["signal"] or (stock["histogram"] and stock["histogram"] < 0)

            if stock["rsi"] > 80 and extended and macd_flat_or_bearish:
                fades.append(stock)
        except:
            continue
    print(f"📉 Found {len(fades)} overbought fade candidates.")
    return fades

def determine_sentiment(label, tags):
    """
    Returns sentiment based on strategy label, or falls back to tag logic.
    """
    # Check strategy label first
    if label in strategy_sentiment_map:
        return strategy_sentiment_map[label]

    # Fallback: tag-based sentiment scoring
    bullish_tags = {"breakout", "momentum"}
    bearish_tags = {"breakdown", "fade"}
    neutral_tags = {"pullback", "reversal"}

    tag_set = set(tags)

    bullish_score = len(tag_set & bullish_tags)
    bearish_score = len(tag_set & bearish_tags)
    neutral_score = len(tag_set & neutral_tags)

    if tag_set <= bullish_tags:
        return "bullish"
    elif tag_set <= bearish_tags:
        return "bearish"
    elif tag_set <= neutral_tags:
        return "neutral"
    elif bullish_score > 0 and bearish_score == 0:
        return "bullish-leaning"
    elif bearish_score > 0 and bullish_score == 0:
        return "bearish-leaning"
    else:
        return "neutral"
    

def score_strategy_matches(tech_snapshots):
    """
    Evaluates each stock against all defined strategies.
    Returns a list of dicts with score and match tags.
    """
    scored = []

    for stock in tech_snapshots:
        matches = []

        # Strategy 1: Breakout
        try:
            near_resistance = stock["resistance"] and stock["price"] >= stock["resistance"] * 0.95
            macd_bullish = stock["macd"] > stock["signal"] or (stock["histogram"] and stock["histogram"] > 0)
            if 50 < stock["rsi"] < 70 and stock["rvol"] > 1.2 and near_resistance and macd_bullish:
                matches.append("breakout")
        except: pass

        # Strategy 2: Breakdown
        try:
            near_support = stock["support"] and stock["price"] <= stock["support"] * 1.05
            macd_bearish = stock["macd"] < stock["signal"] or (stock["histogram"] and stock["histogram"] < 0)

            if stock["rsi"] < 50 and stock["rvol"] > 1.2 and near_support and macd_bearish:
                matches.append("breakdown")
        except: pass

        # Strategy 3: Momentum
        try:
            if stock["rsi"] > 70 and stock["rvol"] > 2.0 and stock["price"] > stock["resistance"]:
                matches.append("momentum")
        except: pass

        # Strategy 4: Pullback
        try:
            if 40 <= stock["rsi"] <= 50 and stock["macd"] > stock["signal"] and stock["price"] <= stock["support"] * 1.05:
                matches.append("pullback")
        except: pass

        # Strategy 5: Reversal
        try:
            if abs(stock["histogram"]) < 0.1:
                matches.append("reversal")
        except: pass

        # Strategy 6: Fade
        try:
            extended = stock["resistance"] and stock["price"] > stock["resistance"] * 1.05
            macd_flat_or_bearish = stock["macd"] < stock["signal"] or (stock["histogram"] and stock["histogram"] < 0)

            if stock["rsi"] > 75 and extended and macd_flat_or_bearish:
                matches.append("fade")
        except: pass
        
        #2.0 new additions
        # slingshot
        try:
            if stock["rvol"] > 2.5 and stock["price"] >= stock["support"] and stock["macd"] > stock["signal"] and stock["rsi"] > 40:
                matches.append("slingshot")
        except: pass

        # consolidation
        try:
            if stock["rvol"] < 0.9 and abs(stock["histogram"]) < 0.05 and 40 < stock["rsi"] < 60:
                matches.append("consolidation")
        except: pass

        # parabolic
        try:
            if stock["rvol"] > 3 and stock["rsi"] > 80 and stock["price"] > stock["resistance"] * 1.1:
                matches.append("parabolic")
        except: pass

        # # Strategy 7: VWAP Reclaim
        # try:
        #     if stock.get("vwap") and stock.get("prev_price"):
        #         prev_below = stock["prev_price"] < stock["vwap"]
        #         now_above = stock["price"] > stock["vwap"]
        #         if prev_below and now_above:
        #             matches.append("vwap_reclaim")
        # except: pass

        # # Strategy 8: ATR Expansion
        # try:
        #     if stock.get("atr") and stock.get("price"):
        #         if (stock["atr"] / stock["price"]) > 0.04:
        #             matches.append("atr_expansion")
        # except: pass

        if matches:
            stock["strategy_score"] = len(matches)
            stock["strategy_tags"] = matches
            stock["strategy_label"] = label_strategy_combo(matches)
            stock["sentiment"] = determine_sentiment(stock["strategy_label"], matches)
            scored.append(stock)
            
            scored.append(stock)
    print(f"🧠 Scored {len(scored)} stocks with at least 1 matching strategy.")
    return scored

def store_scored_setups(scored_stocks):
    """
    Saves scored stocks and strategy matches into StockData.
    Updates existing records or inserts new ones.
    Tracks consecutive days stocks appear in the strategy list.
    """
    from webapp import db
    from webapp.models import StockData  # ✅ Add this!
    from stock_analysis import label_strategy_combo  # Make sure it's imported correctly
    from datetime import datetime, timedelta

    today_symbols = set()
    today = datetime.utcnow().date()

    for stock in scored_stocks:
        try:
            symbol = stock["symbol"]
            today_symbols.add(symbol)
            existing = StockData.query.filter_by(symbol=symbol).first()

            tags_list = stock.get("strategy_tags", [])
            tags_str = ",".join(tags_list)
            score = stock.get("strategy_score", 0)
            label = label_strategy_combo(tags_list)
            confidence = calculate_confidence_score(stock)

            if existing:
                # ✅ Track consecutive days
                last_seen = existing.last_updated.date() if existing.last_updated else None

                if existing.strategy_tags:
                    if last_seen == today:
                        # Already updated today – do not increment again
                        pass
                    elif last_seen == today - timedelta(days=1):
                        existing.days_in_a_row = (existing.days_in_a_row or 1) + 1
                    else:
                        existing.days_in_a_row = 1
                else:
                    existing.days_in_a_row = 1

                existing.sentiment = stock.get("sentiment")  # in the update block
                existing.confidence_score = confidence
                existing.strategy_tags = tags_str
                existing.strategy_score = score
                existing.strategy_label = label
                existing.price = stock["price"]
                existing.last_updated = datetime.utcnow()
            else:
                new_entry = StockData(
                    sentiment=stock.get("sentiment"),
                    confidence_score=confidence,
                    symbol=symbol,
                    name="Unknown",  # Replace if you fetch company name later
                    price=stock["price"],
                    change_percent=0.0,
                    change_amount=0.0,
                    volume=0,
                    category="strategy",
                    summary_text=None,
                    strategy_tags=tags_str,
                    strategy_score=score,
                    strategy_label=label,
                    days_in_a_row=1
                )
                db.session.add(new_entry)

        except Exception as e:
            print(f"⚠️ Could not store {stock.get('symbol', 'UNKNOWN')}: {e}")
            continue

    try:
        # ✅ Phase 3 cleanup: delete previous strategy stocks not in today's list
        from webapp.models import StockData, StockNews  # Ensure import if not already
        referenced_symbols = {row.symbol for row in db.session.query(StockNews.symbol).distinct()}

        # ✅ Skip deleting strategy stocks that are still referenced in stock_news
        db.session.query(StockData).filter(
            StockData.category == "strategy",
            ~StockData.symbol.in_(today_symbols),
            ~StockData.symbol.in_(referenced_symbols)
        ).delete(synchronize_session=False)

        db.session.commit()
        print(f"💾 Stored {len(scored_stocks)} strategy-matching stocks in database.")
            
    except IntegrityError as e:
        db.session.rollback()
        print(f"🚫 DB Commit Error: {e}")
       
def label_strategy_combo(tags):
    """
    Assigns a high-level label based on combinations of strategy tags.
    Used to prioritize multi-signal setups with higher urgency.
    """
    tags = set(tags)

    # 🚨 Priority: 4-strategy power combos
    if len(tags) >= 4:
        # 🚀 Compression breakout after coiling and slingshotting
        if {"consolidation", "breakout", "momentum", "slingshot"} <= tags:
            return "Compression Breakout"

        # ⚡ Failed breakout after vertical run — classic blow-off
        if {"parabolic", "momentum", "fade", "reversal"} <= tags:
            return "Blow-Off Top"

        # 🧨 Full exhaustion breakout scenario
        if {"breakout", "momentum", "reversal", "fade"} <= tags:
            return "Parabolic Exhaustion"

        # 💣 Breakdown losing steam — reversal forming
        if {"breakdown", "momentum", "reversal", "fade"} <= tags:
            return "Capitulation Event"

        # 💥 Failed bounce after pullback — weak recovery
        if {"pullback", "momentum", "fade", "reversal"} <= tags:
            return "Failed Bounce"

        # 🔄 Slam off support with force
        if {"pullback", "reversal", "momentum", "slingshot"} <= tags:
            return "Slingshot Reversal"

        return "Multi-Signal Convergence"


    # ⚡ Key 3-tag setups
    if {"pullback", "reversal", "consolidation"} <= tags:
        return "Coiled Reversal"
    if {"pullback", "reversal", "momentum"} <= tags:
        return "Momentum Slingshot"
    if {"breakout", "momentum", "reversal"} <= tags:
        return "Breakout Reversal"
    if {"breakdown", "reversal", "fade"} <= tags:
        return "Capitulation Reversal"
    if {"pullback", "breakout", "momentum"} <= tags:
        return "Coiled Breakout"
    if {"pullback", "reversal", "fade"} <= tags:
        return "Failed Bounce Attempt"
    if {"breakout", "momentum", "fade"} <= tags:
        return "Momentum Exhaustion"
    if {"breakdown", "fade", "reversal"} <= tags:
        return "Bleed and Reversal"
    if {"pullback", "breakdown", "reversal"} <= tags:
        return "Support Breakdown Trap"
    if {"breakout", "fade", "reversal"} <= tags:
        return "Breakout Failure"
    if {"fade", "momentum", "reversal"} <= tags:
        return "Momentum Flip"
    if {"consolidation", "breakout", "momentum"} <= tags:
        return "Coiled Spring"
    if {"parabolic", "fade", "reversal"} <= tags:
        return "Blow-Off Top"
    # 🧼 Fallback for unknown 3-tag setups
    if len(tags) == 3:
        return "Triple Signal"

    # 🔁 Common 2-tag combos
    if {"consolidation", "breakout"} <= tags:
        return "Range Breakout"
    if "breakout" in tags and "momentum" in tags:
        return "Range Expansion"
    if "breakout" in tags and "reversal" in tags:
        return "Breakout Failure Risk"
    if "pullback" in tags and "reversal" in tags:
        return "Buyable Dip"
    if "breakdown" in tags and "reversal" in tags:
        return "Oversold Reversal"
    if "fade" in tags and "reversal" in tags:
        return "Exhaustion Reversal"
    if "pullback" in tags and "momentum" in tags:
        return "Trend Continuation"
    if "reversal" in tags and "momentum" in tags:
        return "V-Shaped Recovery"
    if "breakdown" in tags and "fade" in tags:
        return "Dead Cat Bounce"
    if "breakdown" in tags and "pullback" in tags:
        return "Downtrend Continuation"
    if "pullback" in tags and "fade" in tags:
        return "Failed Recovery"
    if "momentum" in tags and "fade" in tags:
        return "Momentum Exhaustion"
    if "pullback" in tags and "slingshot" in tags:
        return "Aggressive Reversal"
    if "consolidation" in tags and "momentum" in tags:
        return "Tight Breakout Setup"

    # ✨ Default fallback
    if len(tags) >= 2:
        return "Multi-Signal Setup"
    else:
        return None  # ⛔️ No label for single-tag stocks

# ✅ Add this function to your `stock_analysis.py` or a helper module.

def calculate_confidence_score(stock):
    """
    Assigns a confidence score to a stock based on technical data and strategy type.
    Adjusts scoring logic based on whether the setup is bullish or bearish.
    """
    score = 0
    tags = set(stock.get("strategy_tags", []))
    label = stock.get("strategy_label")
    label = label.lower() if label else ""

    # 🟥 Bearish tags and labels
    bearish_keywords = {"breakdown", "fade", "capitulation", "flush", "dead", "exhausted", "bleed"}

    is_bearish = any(tag in bearish_keywords for tag in tags) or any(kw in label for kw in bearish_keywords)

    try:
        score += stock.get("strategy_score", 0) * 5

        rsi = stock.get("rsi")
        rvol = stock.get("rvol")
        hist = stock.get("histogram")
        price = stock.get("price")
        support = stock.get("support")
        resistance = stock.get("resistance")

        # 🔁 RSI scoring
        if rsi is not None:
            if is_bearish:
                if rsi > 80:
                    score += 4  # Overbought = likely fade
                elif rsi > 70:
                    score += 3
                elif rsi < 30:
                    score += 1  # Too oversold to short
            else:
                if 45 <= rsi <= 55:
                    score += 4
                elif rsi > 70:
                    score += 2
                elif rsi < 30:
                    score += 2

        # 🔁 RVOL scoring
        if rvol:
            if rvol >= 2:
                score += 5
            elif rvol >= 1.5:
                score += 3
            elif rvol >= 1.0:
                score += 1

        # 🔁 Histogram momentum
        if hist:
            if is_bearish and hist < -1:
                score += 3
            elif is_bearish and hist < -0.5:
                score += 2
            elif not is_bearish and hist > 1:
                score += 3
            elif not is_bearish and hist > 0.5:
                score += 2

        # 🔁 Proximity to key levels
        if price and support and price <= support * 1.05:
            score += 2 if is_bearish else 1
        if price and resistance and price >= resistance * 0.95:
            score += 2 if not is_bearish else 1

        # 🔁 Consecutive day bonus
        days = stock.get("days_in_a_row", 1)
        if days >= 5:
            score += 6
        elif days == 4:
            score += 4
        elif days == 3:
            score += 3
        elif days == 2:
            score += 2
    
    except Exception as e:
        print(f"⚠️ Confidence score error for {stock.get('symbol')}: {e}")

    return score


if __name__ == "__main__":
    app = create_app()

    from stock_analysis import store_scored_setups  # ✅ Add this if not imported
    from collections import defaultdict

    with app.app_context():
        snapshot = fetch_market_snapshot()
        print(">>> Calling get_prequalified_stocks")
        prequalified = get_prequalified_stocks(
            snapshot,
            min_price=5,
            min_volume=3_000_000,
            # min_change_pct=-5,
            # min_market_cap=1_000_000_000,
            min_prev_volume=1_000_000,
        )

        tech_snapshots = run_technical_analysis(prequalified)

        # 🧠 Run each strategy filter
        breakout = find_breakout_candidates(tech_snapshots)
        breakdown = find_breakdown_candidates(tech_snapshots)
        momentum = find_momentum_surge_candidates(tech_snapshots)
        pullbacks = find_pullback_buy_zone_candidates(tech_snapshots)
        reversals = find_reversal_candidates(tech_snapshots)
        fades = find_overbought_fade_candidates(tech_snapshots)

        # 🧠 Score everything
        scored_stocks = score_strategy_matches(tech_snapshots)

        # 💾 Store to DB with tracking & cleanup
        print("💾 Storing to DB...")
        store_scored_setups(scored_stocks)

        # 🔎 Individual Strategy Results
        strategy_sections = [
            ("📊 BREAKOUT CANDIDATES:", breakout, "➡️"),
            ("📉 BREAKDOWN CANDIDATES:", breakdown, "⬇️"),
            ("⚡ MOMENTUM SURGE CANDIDATES:", momentum, "⚡"),
            ("🔁 PULLBACK BUY ZONE CANDIDATES:", pullbacks, "↩️"),
            ("🔄 REVERSAL CANDIDATES:", reversals, "🔃"),
            ("📉 OVERBOUGHT FADE CANDIDATES:", fades, "📉"),
        ]

        for title, group, emoji in strategy_sections:
            print(f"\n{title}")
            for stock in group:
                print(f"{emoji} {stock['symbol']} @ ${stock['price']:.2f}")

        # 🧠 FINAL: All strategy-matching stocks sorted by score
        print("\n📈 FINAL STRATEGY OUTPUT (sorted by strategy score):\n")

        sorted_scored = sorted(scored_stocks, key=lambda x: x.get('strategy_score', 0), reverse=True)
        for stock in sorted_scored:
            print(f"🔹 {stock['symbol']} | Price: ${stock['price']:.2f} | Score: {stock['strategy_score']} | Days: {stock.get('days_in_a_row', 1)} | Sentiment: {stock.get('sentiment', 'n/a')}")
            print(f"    Strategies: {', '.join(stock['strategy_tags'])}")
            if stock.get("strategy_label"):
                print(f"    Label: {stock['strategy_label']}")
            print("-" * 50)

        # 📊 Group by Label
        print("\n📈 FINAL STRATEGY OUTPUT GROUPED BY LABEL:\n")
        label_groups = defaultdict(list)
        for stock in scored_stocks:
            label = stock.get("strategy_label")
            if label:
                label_groups[label].append(stock)

        for label, stocks in label_groups.items():
            print(f"🔖 {label} ({len(stocks)} stocks)")
            print("-" * (len(label) + 20))
            for stock in stocks:
                print(f"🔹 {stock['symbol']} | ${stock['price']:.2f} | Score: {stock['strategy_score']} | Days: {stock.get('days_in_a_row', 1)} | Sentiment: {stock.get('sentiment', 'n/a')}")
                print(f"    Tags: {', '.join(stock.get('strategy_tags', []))}")
            print("\n")

        
        # from webapp import db
        # from webapp.models import StockData

        # # Reset days_in_a_row to 0 for all strategy stocks
        # stocks = StockData.query.filter(StockData.category == "strategy").all()
        # for stock in stocks:
        #     stock.days_in_a_row = 0
        # db.session.commit()

        # print("✅ Reset all days_in_a_row to 0")


            