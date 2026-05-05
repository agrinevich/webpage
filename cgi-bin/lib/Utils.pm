package Utils;

use strict;
use warnings;
use utf8;

use English qw( -no_match_vars );
use Carp    qw( croak );
use Path::Tiny;
use Encode                qw(decode encode);
use Number::Bytes::Human  qw(format_bytes);
use File::Copy::Recursive qw(dircopy pathempty);
use Archive::Zip          qw( :ERROR_CODES :CONSTANTS );

our $VERSION = '0.1';

sub format_fsize {
    my ($size) = @_;
    return format_bytes($size);
}

sub read_dir {
    my (%args) = @_;

    my $dir_str = $args{dir};
    my $path    = Path::Tiny->new($dir_str);

    return ( [], [] ) if !( $path->exists && $path->is_dir );

    my @dirs;
    my @files;
    my @o_children = $path->children;
    foreach my $o_child (@o_children) {
        if   ( $o_child->is_dir ) { push @dirs,  $o_child->basename; }
        else                      { push @files, $o_child->basename; }
    }

    return ( \@dirs, \@files );
}

sub read_file {
    my (%args) = @_;

    my $file = $args{file};

    return Path::Tiny->new($file)->slurp_utf8;
}

sub write_file {
    my (%args) = @_;

    my $file = $args{file};
    my $body = $args{body};

    return Path::Tiny->new($file)->spew($body);
}

sub move_file {
    my (%args) = @_;

    my $src = $args{src};
    my $dst = $args{dst};

    return Path::Tiny->new($src)->move($dst);
}

sub copy_file {
    my (%args) = @_;

    my $src = $args{src};
    my $dst = $args{dst};

    return Path::Tiny->new($src)->copy($dst);
}

sub make_path {
    my (%args) = @_;

    my $path = $args{path};

    my $dir = Path::Tiny->new($path);

    return $dir->mkpath;
}

sub move_dir {
    my (%args) = @_;

    my $src_dir = $args{src_dir};
    my $dst_dir = $args{dst_dir};

    return 'error: ' . $src_dir . ' doesnt exist' if !-d $src_dir;

    my $success = File::Copy::Recursive::dirmove( $src_dir, $dst_dir );

    return $success ? undef : 'error: ' . $!;
}

sub copy_dir {
    my (%args) = @_;

    my $src_dir = $args{src_dir};
    my $dst_dir = $args{dst_dir};

    # my $s_dir = Path::Tiny->new($src_dir);
    # if ( !$s_dir->is_dir() ) {
    #     croak( 'Failed to copy_dir_recurs: ' . $s_dir . ' does not exist!' );
    # }

    # if dst_dir exists - delete it first
    # my $o_dir = Path::Tiny->new($dst_dir);
    # if ( $o_dir->is_dir() ) {
    #     empty_dir_recursive(
    #         dir => $dst_dir,
    #     );
    #     rmdir $dst_dir;
    # }

    my ( $total_qty, $dirs_qty, $depth ) = File::Copy::Recursive::dircopy( $src_dir, $dst_dir )
        or croak $OS_ERROR;

    return ( $total_qty, $dirs_qty, $depth );
}

sub empty_dir {
    my (%args) = @_;

    my $dir = $args{dir};

    File::Copy::Recursive::pathempty($dir)
        or croak $OS_ERROR;

    return;
}

sub create_zip {
    my (%args) = @_;

    my $src_dir = $args{src_dir};
    my $dst_dir = $args{dst_dir};
    my $name    = $args{name};

    my $file = $dst_dir . q{/} . $name . '.zip';

    my $zip = Archive::Zip->new();
    $zip->addTree( $src_dir, $name );
    if ( $zip->writeToFileNamed($file) != AZ_OK ) {
        croak 'write error';
    }

    return $file;
}

sub extract_zip {
    my (%args) = @_;

    my $file    = $args{file};
    my $dst_dir = $args{dst_dir};

    my $zip = Archive::Zip->new();
    my $rs  = $zip->read($file);

    if ( $rs != AZ_OK ) {
        return 'Failed to read: ' . $file;
    }

    my $real_dir = path($dst_dir)->realpath;

    my $es = $zip->extractTree( undef, $real_dir );

    return $es == AZ_OK ? q{} : 'Failed to extract';
}

sub translit {
    my (%args) = @_;

    my $skip_decode = $args{skip_decode};
    my $input       = $args{input};

    my $text = q{};
    if ($skip_decode) {
        $text = $input;
    }
    else {
        $text = decode( 'UTF-8', $input );
    }

    $text =~ s/А/A/g;
    $text =~ s/а/a/g;
    $text =~ s/Б/B/g;
    $text =~ s/б/b/g;
    $text =~ s/В/V/g;
    $text =~ s/в/v/g;
    $text =~ s/Г/G/g;
    # $text =~ s/Ґ/G/g;   # ukr
    $text =~ s/г/g/g;
    # $text =~ s/ґ/g/g;   # ukr
    $text =~ s/Д/D/g;
    $text =~ s/д/d/g;
    $text =~ s/Е/E/g;
    # $text =~ s/Є/E/g;   # ukr
    $text =~ s/е/e/g;
    # $text =~ s/є/e/g;   # ukr
    $text =~ s/Ё/E/g;
    $text =~ s/ё/e/g;
    $text =~ s/Ж/Zh/g;
    $text =~ s/ж/zh/g;
    $text =~ s/З/Z/g;
    $text =~ s/з/z/g;
    $text =~ s/И/I/g;
    # $text =~ s/І/I/g;   # ukr
    # $text =~ s/Ї/I/g;   # ukr
    $text =~ s/и/i/g;
    # $text =~ s/і/i/g;   # ukr
    # $text =~ s/ї/i/g;   # ukr
    $text =~ s/Й/Y/g;
    $text =~ s/й/y/g;
    $text =~ s/К/K/g;
    $text =~ s/к/k/g;
    $text =~ s/Л/L/g;
    $text =~ s/л/l/g;
    $text =~ s/М/M/g;
    $text =~ s/м/m/g;
    $text =~ s/Н/N/g;
    $text =~ s/н/n/g;
    $text =~ s/О/O/g;
    $text =~ s/о/o/g;
    $text =~ s/П/P/g;
    $text =~ s/п/p/g;
    $text =~ s/Р/R/g;
    $text =~ s/р/r/g;
    $text =~ s/С/S/g;
    $text =~ s/с/s/g;
    $text =~ s/Т/T/g;
    $text =~ s/т/t/g;
    $text =~ s/У/U/g;
    $text =~ s/у/u/g;
    $text =~ s/Ф/F/g;
    $text =~ s/ф/f/g;
    $text =~ s/Х/Kh/g;
    $text =~ s/х/kh/g;
    $text =~ s/Ц/C/g;
    $text =~ s/ц/c/g;
    $text =~ s/Ч/Ch/g;
    $text =~ s/ч/ch/g;
    $text =~ s/Ш/Sh/g;
    $text =~ s/ш/sh/g;
    $text =~ s/Щ/Shch/g;
    $text =~ s/щ/shch/g;
    $text =~ s/Ь//g;
    $text =~ s/ь//g;
    $text =~ s/Ы/Y/g;
    $text =~ s/ы/y/g;
    $text =~ s/Ъ//g;
    $text =~ s/ъ//g;
    $text =~ s/Э/E/g;
    $text =~ s/э/e/g;
    $text =~ s/Ю/Yu/g;
    $text =~ s/ю/yu/g;
    $text =~ s/Я/Ya/g;
    $text =~ s/я/ya/g;

    return $text;
}

1;
