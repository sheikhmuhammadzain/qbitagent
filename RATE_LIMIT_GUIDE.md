# 🚦 Rate Limit Handling Guide

## Issue: HTTP 429 "Too Many Requests"

When using **free models** on OpenRouter (like `z-ai/glm-4.5-air:free`), you may encounter rate limiting errors:

```
HTTP/1.1 429 Too Many Requests
```

This happens because free models have strict usage limits to prevent abuse.

---

## ✅ What We Fixed

### Backend (Python) - Automatic Retry with Exponential Backoff

**File**: `llm_integration_streaming.py`

The streaming LLM agent now automatically handles rate limits:

1. **Detects 429 errors** from OpenRouter
2. **Waits with exponential backoff**:
   - Attempt 1: Wait 2 seconds
   - Attempt 2: Wait 4 seconds
   - Attempt 3: Wait 8 seconds
3. **Retries up to 3 times**
4. **Shows user-friendly notifications** in the UI

### Frontend (React) - User Feedback

**File**: `client/src/components/chat/ChatInput.tsx`

The chat input now displays helpful toast notifications:

- **"Rate Limit"**: Shows when hitting the limit with retry countdown
- **"Timeout"**: Shows when request times out
- **Automatic retry**: User doesn't need to do anything

---

## 🎯 Free Model Limitations

### OpenRouter Free Tier Limits

| Model | Rate Limit | Notes |
|-------|-----------|-------|
| `z-ai/glm-4.5-air:free` | ~5 req/min | Shared quota across all users |
| Other free models | Varies | Check OpenRouter docs |

### What Triggers Rate Limits

1. **Too many rapid requests** (< 12 seconds between requests)
2. **High concurrent usage** by all users
3. **Peak hours** when many users are active
4. **Large/complex queries** that take longer to process

---

## 💡 Best Practices

### 1. Wait Between Requests
**Recommended**: Wait 15-30 seconds between queries

```typescript
// The app now handles retries automatically
// Just wait a moment before sending your next question
```

### 2. Use Paid Models for Production
For consistent performance without rate limits:

```python
# In your connect request or config
model = "anthropic/claude-3.5-sonnet"  # Paid, no rate limits
# OR
model = "openai/gpt-4-turbo"  # Paid, no rate limits
```

### 3. Batch Your Questions
Instead of multiple small queries:
```
❌ Bad: "What's the total?" → "Show products" → "Filter by date"
✅ Good: "Show total, products, and filter by date in one response"
```

### 4. Monitor Rate Limit Status
Watch the console logs:
```bash
# Backend shows retry attempts
2025-10-11 19:13:35 - Rate limit hit. Retrying in 2s... (attempt 1/3)
```

---

## 🔧 Configuration Options

### Adjust Retry Settings

Edit `llm_integration_streaming.py`:

```python
# Line ~130
max_retries = 3  # Increase to 5 for more patience
retry_delay = 2  # Change initial delay (seconds)
```

### Change Default Model

Edit `config.py`:

```python
# Use a paid model as default
DEFAULT_MODEL = "anthropic/claude-3.5-sonnet"
```

Or select a different model in the UI sidebar before connecting.

---

## 📊 Retry Logic Flow

```
User sends message
    ↓
Backend calls OpenRouter
    ↓
429 Rate Limit? ───→ NO ──→ Stream response
    ↓ YES
Wait 2 seconds
    ↓
Retry attempt 1
    ↓
429 Again? ───→ NO ──→ Stream response
    ↓ YES
Wait 4 seconds
    ↓
Retry attempt 2
    ↓
429 Again? ───→ NO ──→ Stream response
    ↓ YES
Wait 8 seconds
    ↓
Retry attempt 3
    ↓
Success? ───→ YES ──→ Stream response
    ↓ NO
Show error: "Rate limit exceeded after 3 retries"
```

---

## 🚀 Solutions Summary

### Option 1: Wait (Free) ✅ **Implemented**
- Automatic retry with exponential backoff
- Toast notifications in UI
- Works with free models
- **Downside**: Slower responses during peak times

### Option 2: Upgrade to Paid Model (Recommended)
Switch to a paid model for:
- No rate limits
- Faster responses
- Better quality (Claude 3.5, GPT-4)
- Consistent availability

```bash
# In React UI sidebar:
1. Select "anthropic/claude-3.5-sonnet"
2. Click Connect
3. No more rate limits!
```

### Option 3: Host Your Own Model
Use local models via Ollama:
```bash
# Install Ollama
# Run: ollama run llama2
# Update config to use local endpoint
```

---

## 🎓 Example Usage

### Testing Rate Limits

1. **Send a question**:
   ```
   User: "Tell me about this data"
   ```

2. **If rate limited, you'll see**:
   ```
   Toast: "Rate limit hit. Retrying in 2s... (attempt 1/3)"
   ```

3. **Backend automatically retries**:
   ```
   Console: Waiting 2s before retry...
   Console: Retry attempt 1 succeeded!
   ```

4. **Response streams normally**:
   ```
   AI: "Based on the data, here's what I found..."
   ```

### Avoiding Rate Limits

**Bad Pattern** (triggers rate limits):
```
Question 1 → Wait 5s → Question 2 → Wait 5s → Question 3
```

**Good Pattern** (avoids rate limits):
```
Question 1 → Wait 20s → Question 2 → Wait 20s → Question 3
```

---

## 📝 Error Messages Explained

### "Rate limit hit. Retrying in Xs..."
- **Cause**: Too many requests
- **Action**: System is automatically retrying
- **You**: Just wait, no action needed

### "Rate limit exceeded after 3 retries"
- **Cause**: Persistent rate limiting
- **Action**: Wait 2-3 minutes before trying again
- **You**: Consider switching to a paid model

### "Request timeout. Retrying..."
- **Cause**: OpenRouter server slow or overloaded
- **Action**: System is retrying
- **You**: No action needed

---

## 🔍 Debugging Rate Limits

### Check Backend Logs
```bash
python run_fixed.py

# Look for:
# INFO - HTTP Request: POST https://openrouter.ai/... "HTTP/1.1 429 Too Many Requests"
# INFO - Rate limit hit. Retrying in 2s...
```

### Check Frontend Console
```javascript
// Open browser DevTools (F12)
// Console tab shows:
// "Rate limit toast displayed"
// "Retry countdown: 2s"
```

### Test Retry Logic
```bash
# Send multiple rapid requests to trigger rate limit
# Watch console for retry attempts
# Verify exponential backoff: 2s → 4s → 8s
```

---

## ✅ Success Indicators

Your rate limit handling is working when:

1. ✅ **Toast appears** when rate limited
2. ✅ **Automatic retry** without error
3. ✅ **Response streams** after retry
4. ✅ **No manual intervention** needed
5. ✅ **Backend logs** show retry attempts

---

## 🎯 Quick Fix Checklist

If you hit rate limits:

- [ ] Wait 1-2 minutes before next request
- [ ] Check if using a free model (ends with `:free`)
- [ ] Verify toast notifications appear
- [ ] Check backend logs for retry attempts
- [ ] Consider switching to paid model
- [ ] Space out requests by 15-30 seconds

---

## 💰 Recommended Paid Models

For production use without rate limits:

| Model | Cost | Best For |
|-------|------|----------|
| `anthropic/claude-3.5-sonnet` | ~$3/M tokens | Best overall quality |
| `openai/gpt-4-turbo` | ~$10/M tokens | OpenAI ecosystem |
| `google/gemini-pro-1.5` | ~$2/M tokens | Budget-friendly |
| `meta-llama/llama-3.1-70b` | ~$0.50/M tokens | Cost-effective |

**Add your OpenRouter API key** with credits to use paid models.

---

## 📞 Support

If rate limits persist:

1. Check OpenRouter status: https://status.openrouter.ai
2. Verify API key has credits
3. Review OpenRouter rate limit docs
4. Consider model alternatives
5. Contact OpenRouter support

---

**Your app now handles rate limits gracefully with automatic retries!** 🎉

Just wait a moment between requests and let the system handle retries automatically.
