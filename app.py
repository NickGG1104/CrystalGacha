from flask import Flask, render_template, request, jsonify
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import scoped_session, sessionmaker, declarative_base
from sqlalchemy.sql import func
import random

app = Flask(__name__)
app.jinja_env.variable_start_string = '[['
app.jinja_env.variable_end_string = ']]'

engine = create_engine('sqlite:///lottery.db')
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base = declarative_base()

# ==========================================
# 資料庫模型 (Models)
# ==========================================
class Participant(Base):
    __tablename__ = 'participants'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    is_drawn = Column(Boolean, default=False) # 新增：是否已被抽過

class DrawHistory(Base):
    __tablename__ = 'draw_history'
    id = Column(Integer, primary_key=True)
    winner_name = Column(String(100), nullable=False)
    draw_time = Column(DateTime, server_default=func.now())

Base.metadata.create_all(bind=engine)

@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()

# ==========================================
# 路由與 API (Routes)
# ==========================================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/participants', methods=['GET'])
def get_participants():
    participants = db_session.query(Participant).all()
    # 回傳包含 is_drawn 狀態的資料
    result = [{'id': p.id, 'name': p.name, 'is_drawn': p.is_drawn} for p in participants]
    return jsonify(result)

@app.route('/api/participants', methods=['POST'])
def add_participant():
    data = request.json or {}
    name = data.get('name')
    if not name:
        return jsonify({'error': '請提供名稱'}), 400
    
    new_participant = Participant(name=name)
    db_session.add(new_participant)
    db_session.commit()
    return jsonify({'id': new_participant.id, 'name': new_participant.name, 'is_drawn': False}), 201

@app.route('/api/participants/<int:p_id>', methods=['DELETE'])
def delete_participant(p_id):
    participant = db_session.get(Participant, p_id)
    if participant:
        db_session.delete(participant)
        db_session.commit()
    return jsonify({'success': True}), 200

@app.route('/api/reset', methods=['POST'])
def reset_pool():
    # 將所有人的狀態重置為未抽過
    db_session.query(Participant).update({Participant.is_drawn: False})
    db_session.commit()
    return jsonify({'success': True}), 200

@app.route('/api/draw', methods=['POST'])
def draw_winner():
    data = request.json or {}
    try:
        count = int(data.get('count', 1))
    except ValueError:
        count = 1

    # 只查詢「尚未被抽過」的參與者
    eligible_participants = db_session.query(Participant).filter_by(is_drawn=False).all()
    
    if not eligible_participants:
        return jsonify({'error': '所有人都已抽過，請重置名單！'}), 400
    
    if count > len(eligible_participants):
        return jsonify({'error': f'剩餘人數 ({len(eligible_participants)}) 不足抽出的數量 ({count})！'}), 400
    
    # 隨機抽出指定數量
    winners = random.sample(eligible_participants, count)
    
    winner_names = []
    for winner in winners:
        winner.is_drawn = True # 標記為已抽出
        winner_names.append(winner.name)
        # 紀錄歷史
        db_session.add(DrawHistory(winner_name=winner.name))
        
    db_session.commit()
    return jsonify({'winners': winner_names})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
