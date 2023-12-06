from flask import Flask,render_template,request,jsonify
from flaskext.mysql import MySQL
from datetime import datetime,timedelta
import pymysql
app = Flask(__name__)
mysql = MySQL()
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'root'
app.config['MYSQL_DATABASE_DB'] = 'librarydb'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)



@app.route("/")
def home():
    return render_template('index.html')


@app.route("/search", methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        data = request.form['search']
        if data=='':
            return render_template('search.html')
        try:
            conn = mysql.connect()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            query = "SELECT * FROM books WHERE ISBN13=%s OR title LIKE %s OR author LIKE %s"
            cursor.execute(query, (data, f"%{data}%", f"%{data}%"))
            users = cursor.fetchall()
            cursor.execute('Select ISBN13 from book_loans;')
            books = cursor.fetchall()
            books = [i.get('ISBN13') for i in books]
            return render_template('search.html', data=users,books=books)
        except Exception as e:
            print(f"Error: {e}")
        finally:
            cursor.close()
            conn.close()
    return render_template('search.html')


@app.route("/checkout",methods=['GET','POST'])
def checkout():
    if request.method == 'POST':
        data = list(set(request.json.get('selectedBooks')))
        if len(data)>3:
            return jsonify({'error':"Cannot select more then 3 books"})
        cardNumber = request.json.get('cardNumber')
        try:
            current_date = datetime.now().date()
            new_date = current_date + timedelta(days=14)
            conn = mysql.connect()
            cursor = conn.cursor()
            cursor.execute(f"Select * from borrowers WHERE card_id='{cardNumber}'")
            user = cursor.fetchall()
            if len(user)==0:
                return jsonify({'error':"Please Create Borrower Account."})
            cursor.execute(f"Select * from book_loans WHERE card_id='{cardNumber}'")
            no_of_books = cursor.fetchall()    
            if len(no_of_books)>=3:
                return jsonify({'error':"You Cannot take more then 3 books with this Card Number"})    
            for i in data:  
                cursor.execute(f"""INSERT INTO `book_loans` (`ISBN13`, `card_id`, `date_out`, `due_date`, `date_in`) VALUES ('{i}', '{cardNumber}', '{current_date}', '{new_date}', NULL);""")
                conn.commit()   
            return jsonify({'success':"Your Book has been checked out"})
        except Exception as e:
            error_msg = str(e).lower()
            if 'duplicate' in error_msg:
                return jsonify({'error':"Book is already taken"})
            print(f'Error: {e}')
        finally:
            cursor.close()
            conn.close()

        return jsonify({'success':'wow'})
    return render_template('checkout.html')


@app.route("/checkin",methods=['GET','POST'])
def checkin():
    if request.method == 'POST':
        cardNumber = request.json.get('cardNumber')   
        conn = mysql.connect()
        cursor = conn.cursor()
        cursor.execute(f"Select * from book_loans WHERE card_id='{cardNumber}'")
        books = cursor.fetchall()
        print(books)
        return jsonify({'books':list(books)})
    return render_template('checkin.html')


@app.route("/checkfines", methods=['POST'])
def checkfines():
    if request.method == 'POST':
        isbn = request.json.get('isbn')
        cardNumber = request.json.get('cardNumber')
        conn = mysql.connect()
        cursor = conn.cursor()
        cursor.execute(f"SELECT due_date, date_out FROM book_loans WHERE card_id='{cardNumber}' AND ISBN13='{isbn}'")
        result = cursor.fetchone()
        if result:
            due_date = result[1]
            date_out = result[0]
            due_date = datetime.strptime(due_date, '%Y-%m-%d')
            date_out = datetime.strptime(date_out, '%Y-%m-%d')

            difference_in_days = (datetime.now() - date_out).days
            if difference_in_days > 0:
                fines = float(difference_in_days*0.25)
                return jsonify({'success':f'Your Fine is ${fines}'})
            else:
                cursor.execute(f"DELETE from book_loans WHERE ISBN13='{isbn}' AND card_id='{cardNumber}'")
                conn.commit()
                return jsonify({'success': 'Your book has been checked in'}) 
        else:
            return jsonify({'error': 'there is no such book'})

@app.route("/borrower", methods=['POST', 'GET'])
def borrower():
    if request.method == 'POST':
        try:
            card_id = request.form['card']
            ssn = request.form['ssn']
            first_name = request.form['firstName']
            last_name = request.form['lastName']
            email = request.form['email']
            address = request.form['address']
            city = request.form['city']
            state = request.form['state']
            phone = request.form['phone']

            query = f"""INSERT INTO `borrowers` (`card_id`, `ssn`, `first_name`, `last_name`, `email`, `address`, `city`, `state`, `phone`)
                        VALUES ('{card_id}', '{ssn}', '{first_name}', '{last_name}', '{email}', '{address}', '{city}', '{state}', '{phone}');"""

            conn = mysql.connect()
            cursor = conn.cursor()
            cursor.execute(query)
            conn.commit()

            return render_template('search.html')
        except Exception as e:
            print(f"Error: {e}")
        finally:
            cursor.close()
            conn.close()

    return render_template('borrower.html')

@app.route("/fine",methods=['GET','POST'])
def fine():
    if request.method == 'POST':
        cardNumber = request.json.get('cardNumber')
        print(cardNumber)
        conn = mysql.connect()
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM book_loans WHERE card_id='{cardNumber}'")
        result = cursor.fetchall()
        res = []
        for i in result:
            due_date = i[4]
            date_out = i[3]
            due_date = datetime.strptime(due_date, '%Y-%m-%d')
            date_out = datetime.strptime(date_out, '%Y-%m-%d')
            difference_in_days = (datetime.now() - due_date).days
            if difference_in_days > 0:
                fines = float(difference_in_days*0.25)
                res.append({'ISBN':i[1],'due_date':i[3],'date_out':i[4],'fine':fines})
        return jsonify({'books':list(res)})
        
    return render_template('fine.html')

if __name__ == "__main__":
    app.run(debug=True)
