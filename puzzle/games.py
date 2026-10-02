from copy import deepcopy
from datetime import datetime, timedelta, timezone
from random import SystemRandom

GAMES = {'lights', 'slide', 'memory', 'flood'}
DIFFICULTIES = {'easy', 'tricky'}
IST = timezone(timedelta(hours=5, minutes=30))
rng = SystemRandom()

def neighbors(i, n):
    return ([i-1] if i % n else []) + ([i+1] if i % n < n-1 else []) + ([i-n] if i >= n else []) + ([i+n] if i < n*(n-1) else [])

def territory(board, n):
    seen, queue = {0}, [0]
    for i in queue:
        for j in neighbors(i, n):
            if j not in seen and board[j] == board[0]:
                seen.add(j)
                queue.append(j)
    return queue

def generate(game, difficulty):
    n = {'lights': (4,5), 'slide': (3,4), 'memory': (4,6), 'flood': (6,9)}[game][difficulty == 'tricky']
    board = []
    if game == 'lights':
        board = [0] * (n*n)
        for i in rng.sample(range(n*n), 5 if n == 4 else 11):
            for j in [i] + neighbors(i, n):
                board[j] ^= 1
        if not any(board):
            for j in [0] + neighbors(0, n):
                board[j] ^= 1
    elif game == 'slide':
        board = list(range(1, n*n)) + [0]
        empty, previous = n*n-1, -1
        for _ in range(55 if n == 3 else 140):
            next_tile = rng.choice([i for i in neighbors(empty, n) if i != previous])
            board[empty], board[next_tile] = board[next_tile], board[empty]
            previous, empty = empty, next_tile
        if board == list(range(1, n*n)) + [0]:
            j = neighbors(empty, n)[0]
            board[empty], board[j] = board[j], board[empty]
    elif game == 'memory':
        board = [i // 2 for i in range(n*n)]
        rng.shuffle(board)
    else:
        board = [rng.randrange(6) for _ in range(n*n)]
        if len(set(board)) == 1:
            board[-1] = (board[0] + 1) % 6
    return dict(game=game, difficulty=difficulty, n=n, board=board, matched=[], flipped=[], hideAt=0, moves=0, won=False)

def advance(original, index, now):
    state = deepcopy(original)
    board, n, game = state['board'], state['n'], state['game']
    if state['won']:
        raise ValueError('This attempt is already complete.')
    if type(index) is not int or not 0 <= index < (6 if game == 'flood' else len(board)):
        raise ValueError('Invalid move.')
    if game == 'lights':
        for j in [index] + neighbors(index, n):
            board[j] ^= 1
        state['moves'] += 1
        state['won'] = not any(board)
    elif game == 'slide':
        empty = board.index(0)
        if index not in neighbors(empty, n):
            raise ValueError('Choose a tile next to the empty space.')
        board[empty], board[index] = board[index], board[empty]
        state['moves'] += 1
        state['won'] = board == list(range(1, n*n)) + [0]
    elif game == 'flood':
        if index == board[0]:
            raise ValueError('Choose a different color.')
        for j in territory(board, n):
            board[j] = index
        state['moves'] += 1
        state['won'] = len(set(board)) == 1
    else:
        if len(state['flipped']) == 2:
            if now < state['hideAt']:
                raise ValueError('Wait for the cards to turn back over.')
            state['flipped'], state['hideAt'] = [], 0
        if index in state['matched'] or index in state['flipped']:
            raise ValueError('Choose a hidden card.')
        state['flipped'].append(index)
        if len(state['flipped']) == 2:
            state['moves'] += 1
            a, b = state['flipped']
            if board[a] == board[b]:
                state['matched'].extend([a,b])
                state['flipped'] = []
            else:
                state['hideAt'] = now + 850
        state['won'] = len(state['matched']) == len(board)
    return state

def visible(state, now):
    state = deepcopy(state)
    if len(state['flipped']) == 2 and now >= state['hideAt']:
        state['flipped'] = []
    if state['game'] == 'memory':
        state['board'] = [v if i in state['matched'] or i in state['flipped'] else None for i,v in enumerate(state['board'])]
    return state

def day_key(now):
    return datetime.fromtimestamp(now/1000, IST).date().isoformat()

def reset_at(day):
    start = datetime.fromisoformat(day).replace(tzinfo=IST)
    return int((start + timedelta(days=1)).timestamp()*1000)
