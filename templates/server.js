const express = require('express');
const session = require('express-session');
const passport = require('passport');
const LocalStrategy = require('passport-local').Strategy;
const bodyParser = require('body-parser');
const bcrypt = require('bcrypt');

const app = express();
const PORT = process.env.PORT || 3000;

const users = []; // Simulated database

passport.use(new LocalStrategy({
    usernameField: 'username',
    passwordField: 'password'
}, (username, password, done) => {
    const user = users.find(user => user.username === username);
    if (user && bcrypt.compareSync(password, user.password)) {
        return done(null, user);
    } else {
        return done(null, false, { message: 'Invalid username or password' });
    }
}));

passport.serializeUser((user, done) => {
    done(null, user.id);
});

passport.deserializeUser((id, done) => {
    const user = users.find(user => user.id === id);
    if (user) {
        done(null, user);
    } else {
        done(new Error('User not found'), null);
    }
});

app.use(express.static('public'));
app.use(bodyParser.urlencoded({ extended: true }));
app.use(session({
    secret: 'your_secret_key',
    resave: false,
    saveUninitialized: false
}));
app.use(passport.initialize());
app.use(passport.session());

app.set('view engine', 'ejs');

// Routes
app.get('/', (req, res) => {
    res.redirect('/index1.html');
});

app.get('/index1.html', (req, res) => {
    if (req.isAuthenticated()) {
        res.render('index1', { user: req.user });
    } else {
        res.redirect('/login');
    }
});

app.get('/login', (req, res) => {
    res.render('login');
});

app.post('/login', passport.authenticate('local', {
    successRedirect: '/index1.html',
    failureRedirect: '/login'
}));

app.get('/signup', (req, res) => {
    res.render('signup');
});

app.post('/signup', (req, res) => {
    const { username, password, name } = req.body;
    if (users.some(u => u.username === username)) {
        return res.render('signup', { message: 'User already exists' });
    }
    const hashedPassword = bcrypt.hashSync(password, 10);
    const newUser = {
        id: Date.now().toString(),
        name: name,
        username: username,
        password: hashedPassword
    };
    users.push(newUser);
    req.login(newUser, err => {
        if (err) {
            return res.render('signup', { message: 'Signup failed' });
        }
        res.redirect('/index1.html');
    });
});

app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});
